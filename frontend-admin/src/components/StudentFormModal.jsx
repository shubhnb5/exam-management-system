import { useState } from "react";
import api from "../api";
import Icon from "./Icon";
import Modal from "./Modal";
import { truncate } from "../utils/text";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MOBILE_RE = /^[6-9]\d{9}$/;

function validate(form) {
  const errors = {};
  if (!form.full_name.trim()) errors.full_name = "Student name is required.";
  if (!form.email.trim()) errors.email = "Email is required.";
  else if (!EMAIL_RE.test(form.email.trim())) errors.email = "Enter a valid email address.";
  if (!form.mobile_number) errors.mobile_number = "Mobile number is required.";
  else if (!MOBILE_RE.test(form.mobile_number)) errors.mobile_number = "Enter a valid 10-digit Indian mobile number.";
  if (!form.exam_center_id) errors.exam_center_id = "Please select an exam center.";
  return errors;
}

function FieldError({ message }) {
  return message ? (
    <div className="form-field-error" role="alert">
      <Icon name="alert" size={14} />
      {message}
    </div>
  ) : null;
}

/**
 * Add a single student (student = null) or edit an existing one.
 * Calls onSaved(result) with the API's StudentSaveResult.
 */
export default function StudentFormModal({ student, centers, onClose, onSaved }) {
  const isEdit = !!student;
  const [form, setForm] = useState({
    full_name: student?.full_name || "",
    email: student?.email || "",
    mobile_number: student?.mobile_number || "",
    exam_center_id: student?.exam_center_id ? String(student.exam_center_id) : "",
    generate_admit_card: true,
  });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: "" }));
  }

  function close() {
    if (!busy) onClose();
  }

  async function submit(e) {
    e.preventDefault();
    setMessage("");
    const next = validate(form);
    setErrors(next);
    if (Object.keys(next).length) return;

    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim().toLowerCase(),
      mobile_number: form.mobile_number,
      exam_center_id: Number(form.exam_center_id),
    };
    setBusy(true);
    try {
      const res = isEdit
        ? await api.put(`/admin/students/${student.id}`, payload)
        : await api.post("/admin/students", { ...payload, generate_admit_card: form.generate_admit_card });
      onSaved(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.errors) {
        setErrors(detail.errors);
        setMessage("Please correct the highlighted fields.");
      } else {
        setMessage(typeof detail === "string" ? detail : "Could not save the student. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={isEdit ? "Edit Student" : "Add Student"} onClose={close} wide>
      <form className="student-form" onSubmit={submit} noValidate>
        {!isEdit && (
          <p className="modal-message">
            Use this for a student who was missed in an uploaded sheet. The student sees their admit card in the
            student portal when they log in with this same mobile number.
          </p>
        )}
        {isEdit && student.has_ticket && (
          <p className="modal-message">
            This student already has an admit card. Changing the name, mobile number or exam center updates the
            admit card automatically — the QR code stays the same.
          </p>
        )}

        <label className="field-label field-span">
          Student name
          <input
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            aria-invalid={!!errors.full_name}
            maxLength={120}
            autoFocus
          />
          <FieldError message={errors.full_name} />
        </label>

        <label className="field-label field-span">
          Email
          <input
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            aria-invalid={!!errors.email}
          />
          <FieldError message={errors.email} />
        </label>

        <label className="field-label">
          Mobile number
          <div className="input-with-prefix">
            <span className="input-prefix">+91</span>
            <input
              type="tel"
              inputMode="numeric"
              maxLength={10}
              placeholder="10-digit mobile number"
              value={form.mobile_number}
              onChange={(e) => set("mobile_number", e.target.value.replace(/\D/g, "").slice(0, 10))}
              aria-invalid={!!errors.mobile_number}
            />
          </div>
          <FieldError message={errors.mobile_number} />
        </label>

        <label className="field-label">
          Exam center
          <select
            value={form.exam_center_id}
            onChange={(e) => set("exam_center_id", e.target.value)}
            aria-invalid={!!errors.exam_center_id}
          >
            <option value="" disabled>
              Select exam center...
            </option>
            {centers.map((c) => (
              <option key={c.id} value={c.id} title={c.name}>
                {truncate(c.name)}
              </option>
            ))}
          </select>
          <FieldError message={errors.exam_center_id} />
        </label>

        {!isEdit && (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.generate_admit_card}
              onChange={(e) => set("generate_admit_card", e.target.checked)}
            />
            Generate admit card now
          </label>
        )}

        {message && (
          <div className="error-banner" role="alert">
            <Icon name="alert" size={18} />
            <span>{message}</span>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn-small" onClick={close} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="btn-small btn-primary" disabled={busy}>
            {busy ? "Saving..." : isEdit ? "Save changes" : "Add Student"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
