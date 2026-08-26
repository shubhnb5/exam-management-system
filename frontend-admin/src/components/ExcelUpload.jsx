import { useRef, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import { truncate } from "../utils/text";

export default function ExcelUpload({ centers, onUploaded }) {
  const [examCenterId, setExamCenterId] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const centerSelected = examCenterId !== "";

  async function uploadFile(file) {
    if (!file) return;
    if (!centerSelected) {
      setError("Please select an exam center before uploading.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("exam_center_id", examCenterId);
      const res = await api.post("/admin/students/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      onUploaded && onUploaded();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CollapsibleCard title="Upload Student Excel Sheet">
      <p className="muted">
        Accepts .xlsx, .xlsm, .pdf, or .docx (a table with the same columns). Columns expected: Student Name, Email,
        Mobile Number. Every student in this sheet is assigned to the exam center selected below — upload one sheet
        per center. Re-uploading updates existing students by email without duplicating them (including moving them
        to a different center if re-uploaded under a different selection).
      </p>

      <label className="center-select-label">
        Exam Center for this sheet
        <select value={examCenterId} onChange={(e) => setExamCenterId(e.target.value)}>
          <option value="" disabled>
            Select exam center...
          </option>
          {centers.map((c) => (
            <option key={c.id} value={c.id} title={c.name}>
              {truncate(c.name)}
            </option>
          ))}
        </select>
      </label>

      <div
        className={`dropzone ${dragOver ? "dropzone-active" : ""} ${!centerSelected ? "dropzone-disabled" : ""}`}
        onClick={() => centerSelected && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (centerSelected) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (centerSelected) uploadFile(e.dataTransfer.files[0]);
        }}
      >
        {busy
          ? "Uploading..."
          : centerSelected
            ? "Drag & drop your .xlsx, .pdf, or .docx file here, or click to browse"
            : "Select an exam center above first"}
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xlsm,.pdf,.docx"
          style={{ display: "none" }}
          onChange={(e) => uploadFile(e.target.files[0])}
        />
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="upload-result">
          <div className="stat-row">
            <span className="badge badge-green">{result.upload.new_students} new</span>
            <span className="badge badge-blue">{result.upload.updated_students} updated</span>
            <span className="badge badge-red">{result.upload.error_count} errors</span>
          </div>
          {result.errors.length > 0 && (
            <ul className="error-list">
              {result.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </CollapsibleCard>
  );
}
