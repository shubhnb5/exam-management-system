import { useCallback, useEffect, useState } from "react";
import api from "../api";
import { DistrictOptions } from "../districts";
import AddExamCenterButton from "./AddExamCenterButton";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import Modal from "./Modal";
import Spinner from "./Spinner";
import TimeSlotsModal from "./TimeSlotsModal";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function usageText(c) {
  if (c.can_delete) return "Not in use";
  if (c.scan_count) return "Has attendance history — can be renamed, not deleted";
  return "In use — move or delete its students and teachers to delete it";
}

function EditCenterModal({ center, onClose, onSaved }) {
  const [name, setName] = useState(center.name);
  const [district, setDistrict] = useState(center.district || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    const trimmed = name.trim().replace(/\s+/g, " ");
    if (trimmed.length < 3) {
      setError("Exam center name must be at least 3 characters.");
      return;
    }
    if (!district) {
      setError("Please select the district of the exam center.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api.put(`/admin/exam-centers/${center.id}`, { name: trimmed, district });
      onSaved(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save the exam center.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Edit Exam Center" onClose={() => !busy && onClose()}>
      <form className="modal-form" onSubmit={submit}>
        <p className="modal-message">
          {center.admit_card_count > 0
            ? `${plural(center.admit_card_count, "admit card")} at this center will show the new name and district automatically. QR codes don't change, so printed cards still scan.`
            : "The new name and district appear everywhere this center is used."}
        </p>
        <label className="field-label">
          Exam center name
          <input
            className="modal-input"
            autoFocus
            value={name}
            maxLength={200}
            onChange={(e) => {
              setName(e.target.value);
              if (error) setError("");
            }}
          />
        </label>
        <label className="field-label">
          District
          <select
            className="modal-input"
            value={district}
            onChange={(e) => {
              setDistrict(e.target.value);
              if (error) setError("");
            }}
          >
            <DistrictOptions />
          </select>
        </label>
        {error && (
          <div className="error-banner" role="alert">
            <Icon name="alert" size={18} />
            <span>{error}</span>
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn-small" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="btn-small btn-primary" disabled={busy || !name.trim() || !district}>
            {busy ? "Saving..." : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function ExamCentersPanel({ onChanged }) {
  const { confirm } = useDialog();
  const { showToast } = useToast();
  const [centers, setCenters] = useState(null);
  const [editing, setEditing] = useState(null);
  const [timingsFor, setTimingsFor] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/admin/exam-centers/overview");
      setCenters(res.data);
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load exam centers.");
      setCenters([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function afterChange() {
    await load();
    onChanged && onChanged();
  }

  async function remove(c) {
    const ok = await confirm({
      title: "Delete exam center",
      message: `Delete "${c.name}"? It will no longer appear in any dropdown. This cannot be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    setError("");
    try {
      await api.delete(`/admin/exam-centers/${c.id}`);
      showToast(`Deleted exam center "${c.name}".`, "success");
      await afterChange();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not delete the exam center.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CollapsibleCard
      title={`Exam Centers${centers ? ` (${centers.length})` : ""}`}
      icon="building"
      headerExtra={<AddExamCenterButton onAdded={afterChange} />}
      description="Rename a center or change its district at any time — its admit cards update automatically. A center can be deleted only when no students, teachers or attendance records use it."
    >
      {error && (
        <div className="error-banner" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      )}

      {centers === null ? (
        <Spinner label="Loading exam centers..." />
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Exam Center</th>
                <th>District</th>
                <th>Code</th>
                <th>Students</th>
                <th>Admit Cards</th>
                <th>Teachers</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {centers.length === 0 && (
                <tr>
                  <td colSpan={7} className="empty-state">
                    <div className="empty-state-icon">
                      <Icon name="building" size={24} />
                    </div>
                    No exam centers yet — use Add Exam Center.
                  </td>
                </tr>
              )}
              {centers.map((c) => (
                <tr key={c.id}>
                  <td className="cell-primary cell-wrap" data-label="Exam Center">
                    {c.name}
                  </td>
                  <td data-label="District">
                    {c.district || <span className="muted">Not set — edit to add</span>}
                  </td>
                  <td className="cell-mono" data-label="Code">
                    {c.code}
                  </td>
                  <td className="cell-mono" data-label="Students">
                    {c.student_count}
                  </td>
                  <td className="cell-mono" data-label="Admit Cards">
                    {c.admit_card_count}
                  </td>
                  <td className="cell-mono" data-label="Teachers">
                    {c.teacher_count}
                  </td>
                  <td className="cell-actions" data-label="Action">
                    <div className="row-actions">
                      <button type="button" className="btn-small" onClick={() => setEditing(c)} disabled={busy}>
                        <Icon name="edit" size={16} />
                        Edit
                      </button>
                      <button
                        type="button"
                        className="btn-small"
                        onClick={() => setTimingsFor(c)}
                        disabled={busy}
                        title="Exam timings printed on this center's admit cards"
                      >
                        <Icon name="clock" size={16} />
                        Timings{c.time_slot_count ? ` (${c.time_slot_count})` : ""}
                      </button>
                      <button
                        type="button"
                        className="btn-small btn-danger"
                        onClick={() => remove(c)}
                        disabled={busy || !c.can_delete}
                        title={usageText(c)}
                      >
                        <Icon name="trash" size={16} />
                        Delete
                      </button>
                    </div>
                    {!c.can_delete && <div className="muted cell-sub center-usage">{usageText(c)}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <EditCenterModal
          center={editing}
          onClose={() => setEditing(null)}
          onSaved={async (result) => {
            setEditing(null);
            showToast(
              result.admit_cards_updated
                ? `Saved. ${plural(result.admit_cards_updated, "admit card")} updated.`
                : "Exam center saved.",
              "success"
            );
            await afterChange();
          }}
        />
      )}

      {timingsFor && <TimeSlotsModal center={timingsFor} onClose={() => setTimingsFor(null)} onChanged={load} />}
    </CollapsibleCard>
  );
}
