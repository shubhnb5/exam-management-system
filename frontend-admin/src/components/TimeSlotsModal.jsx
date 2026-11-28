import { useCallback, useEffect, useState } from "react";
import api from "../api";
import Icon from "./Icon";
import Modal from "./Modal";
import Spinner from "./Spinner";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";
import { timingLabel } from "../utils/text";

// The three admit card timetable columns a timing sets (labels as printed on the card).
const FIELDS = [
  { key: "reporting", label: "उपकेंद्रावरील उपस्थिती (reporting)" },
  { key: "last_entry", label: "परीक्षा कक्षातील शेवटच्या प्रवेशाची वेळ (last entry)" },
  { key: "duration", label: "परीक्षेचा प्रत्यक्ष कालावधी (exam time)" },
];

function FieldError({ message }) {
  return message ? (
    <div className="form-field-error" role="alert">
      <Icon name="alert" size={14} />
      {message}
    </div>
  ) : null;
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/**
 * Exam timings (time slots) of one exam center. A timing is chosen when
 * uploading a student sheet; those students' admit cards print it.
 */
export default function TimeSlotsModal({ center, onClose, onChanged }) {
  const { confirm } = useDialog();
  const { showToast } = useToast();
  const [data, setData] = useState(null); // { default, slots } for this center
  const [form, setForm] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/admin/time-slots");
      const next = { default: res.data.default, slots: res.data.slots.filter((s) => s.exam_center_id === center.id) };
      setData(next);
      return next;
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load exam timings.");
      setData({ default: null, slots: [] });
      return null;
    }
  }, [center.id]);

  useEffect(() => {
    load().then((next) => {
      // A new timing starts from the default one, so only the changed parts need typing.
      if (next?.default) setForm({ ...next.default });
      else setForm({ reporting: "", last_entry: "", duration: "" });
    });
  }, [load]);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: "" }));
    if (error) setError("");
  }

  function resetForm() {
    setEditingId(null);
    setErrors({});
    setError("");
    setForm(data?.default ? { ...data.default } : { reporting: "", last_entry: "", duration: "" });
  }

  function startEdit(slot) {
    setEditingId(slot.id);
    setErrors({});
    setError("");
    setForm({ reporting: slot.reporting, last_entry: slot.last_entry, duration: slot.duration });
  }

  async function submit(e) {
    e.preventDefault();
    const payload = {};
    const next = {};
    for (const { key } of FIELDS) {
      payload[key] = (form[key] || "").trim().replace(/\s+/g, " ");
      if (!payload[key]) next[key] = "This field is required.";
    }
    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    setError("");
    try {
      if (editingId) {
        await api.put(`/admin/time-slots/${editingId}`, payload);
        showToast("Exam timing saved. Admit cards generated from now on use it.", "success");
      } else {
        await api.post(`/admin/exam-centers/${center.id}/time-slots`, payload);
        showToast("Exam timing added.", "success");
      }
      const fresh = await load();
      setEditingId(null);
      setErrors({});
      setForm(fresh?.default ? { ...fresh.default } : { reporting: "", last_entry: "", duration: "" });
      onChanged && onChanged();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.errors) {
        setErrors(detail.errors);
      } else {
        setError(typeof detail === "string" ? detail : "Could not save the exam timing.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function remove(slot) {
    const ok = await confirm({
      title: "Delete exam timing",
      message: `Delete the timing "${timingLabel(slot)}"? It will no longer appear when uploading students.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    setError("");
    try {
      await api.delete(`/admin/time-slots/${slot.id}`);
      showToast("Exam timing deleted.", "success");
      if (editingId === slot.id) resetForm();
      await load();
      onChanged && onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not delete the exam timing.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  const editingSlot = editingId ? data?.slots.find((s) => s.id === editingId) : null;

  return (
    <Modal title="Exam Timings" onClose={() => !busy && onClose()} wide>
      <div className="modal-form">
        <p className="modal-message">
          <strong>{center.name}</strong> — add a timing for each batch, then select it under Upload Students: every
          student in that sheet gets it on their admit card (all exam dates). Students uploaded with "Default timing"
          get the admit card template's timing
          {data?.default ? (
            <>
              : <strong>{timingLabel(data.default)}</strong>
            </>
          ) : null}
          .
        </p>

        {data === null ? (
          <Spinner label="Loading exam timings..." />
        ) : (
          // A list rather than a table: it reads the same on phones, laptops
          // and desktops inside the narrow modal (a table would scroll sideways).
          <div className="upload-section">
            <h3 className="upload-section-title">
              <Icon name="clock" size={18} />
              <span>
                {data.slots.length ? plural(data.slots.length, "custom timing") : "No custom timings yet"}
              </span>
            </h3>
            <ul className="refresh-list">
              {data.slots.length === 0 && (
                <li>Every student of this center gets the default timing. Add a timing below for another batch.</li>
              )}
              {data.slots.map((s) => (
                <li key={s.id} aria-current={editingId === s.id ? "true" : undefined}>
                  <strong>{timingLabel(s)}</strong>
                  <div className="muted cell-sub">
                    {plural(s.student_count, "student")} · {plural(s.admit_card_count, "admit card")}
                    {editingId === s.id ? " · editing below" : ""}
                  </div>
                  <div className="stat-row">
                    <button type="button" className="btn-small" onClick={() => startEdit(s)} disabled={busy}>
                      <Icon name="edit" size={16} />
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-small btn-danger"
                      onClick={() => remove(s)}
                      disabled={busy || !s.can_delete}
                      title={s.can_delete ? "Not in use" : "In use by students — can't be deleted"}
                    >
                      <Icon name="trash" size={16} />
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {form && (
        <form className="student-form upload-section" onSubmit={submit} noValidate>
          <div className="modal-title field-span">{editingId ? "Edit timing" : "Add timing"}</div>
          {editingSlot && editingSlot.admit_card_count > 0 && (
            <p className="modal-message">
              {plural(editingSlot.admit_card_count, "admit card")} already generated with this timing keep the old
              timing. Only admit cards generated after saving use the new timing.
            </p>
          )}
          {FIELDS.map(({ key, label }) => (
            <label className="field-label field-span" key={key}>
              {label}
              <input
                value={form[key]}
                maxLength={40}
                onChange={(e) => set(key, e.target.value)}
                aria-invalid={!!errors[key]}
              />
              <FieldError message={errors[key]} />
            </label>
          ))}

          {error && (
            <div className="error-banner" role="alert">
              <Icon name="alert" size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="modal-actions">
            {editingId ? (
              <button type="button" className="btn-small" onClick={resetForm} disabled={busy}>
                Cancel edit
              </button>
            ) : (
              <button type="button" className="btn-small" onClick={onClose} disabled={busy}>
                Close
              </button>
            )}
            <button type="submit" className="btn-small btn-primary" disabled={busy}>
              {busy ? "Saving..." : editingId ? "Save timing" : "Add timing"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
