import { useState } from "react";
import api from "../api";
import Icon from "./Icon";
import Modal from "./Modal";
import { useToast } from "./ToastProvider";

const MIN_LEN = 3;
const MAX_LEN = 200;

export default function AddExamCenterButton({ onAdded }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function close() {
    if (busy) return;
    setOpen(false);
    setName("");
    setError("");
  }

  async function submit(e) {
    e.preventDefault();
    const trimmed = name.trim().replace(/\s+/g, " ");
    if (trimmed.length < MIN_LEN) {
      setError(`Exam center name must be at least ${MIN_LEN} characters.`);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/admin/exam-centers", { name: trimmed });
      showToast(`Exam center "${res.data.name}" added.`, "success");
      setOpen(false);
      setName("");
      onAdded && onAdded(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not add exam center.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="btn-small" onClick={() => setOpen(true)}>
        <Icon name="plus" size={17} />
        Add Exam Center
      </button>
      {open && (
        <Modal title="Add Exam Center" onClose={close}>
          <form className="modal-form" onSubmit={submit}>
            <p className="modal-message">
              The new center will appear in the exam center dropdowns (student upload and teacher accounts).
            </p>
            <label className="field-label">
              Exam center name
              <input
                className="modal-input"
                autoFocus
                value={name}
                maxLength={MAX_LEN}
                placeholder="e.g. Modern College, Shivajinagar, Pune"
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            {error && (
              <div className="error-banner" role="alert">
                <Icon name="alert" size={18} />
                <span>{error}</span>
              </div>
            )}
            <div className="modal-actions">
              <button type="button" className="btn-small" onClick={close} disabled={busy}>
                Cancel
              </button>
              <button type="submit" className="btn-small btn-primary" disabled={busy || !name.trim()}>
                {busy ? "Adding..." : "Add Exam Center"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
