import { useEffect, useRef, useState } from "react";
import api from "../api";
import AddExamCenterButton from "./AddExamCenterButton";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import { truncate } from "../utils/text";
import { useToast } from "./ToastProvider";

export default function ExcelUpload({ centers, onUploaded, onCentersChanged }) {
  const { showToast } = useToast();
  const [examCenterId, setExamCenterId] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const pollRef = useRef(null);

  const centerSelected = examCenterId !== "";

  // The server processes the sheet in the background (a large PDF can take
  // about a minute), so poll for the result. If an upload was already being
  // processed when this page opened (e.g. the admin navigated away and
  // back), pick it up again.
  useEffect(() => {
    api
      .get("/admin/students/upload/status")
      .then((res) => {
        if (res.data.status === "running") {
          setBusy(true);
          pollStatus(0);
        }
      })
      .catch(() => {});
    return () => clearTimeout(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pollStatus(failures) {
    pollRef.current = setTimeout(async () => {
      let res;
      try {
        res = await api.get("/admin/students/upload/status");
      } catch {
        // A brief network hiccup shouldn't abandon a long upload.
        if (failures < 10) {
          pollStatus(failures + 1);
        } else {
          setBusy(false);
          setError("Lost connection while the file was being processed. Check the Students list before uploading again.");
        }
        return;
      }
      if (res.data.status === "running") {
        pollStatus(0);
        return;
      }
      setBusy(false);
      if (res.data.status === "done") {
        const data = res.data.result;
        setResult(data);
        const { new_students, updated_students, error_count } = data.upload;
        showToast(
          `Uploaded: ${new_students} new, ${updated_students} updated${error_count ? `, ${error_count} rows skipped` : ""}.`,
          error_count ? "error" : "success"
        );
        onUploaded && onUploaded();
      } else if (res.data.status === "error") {
        const msg = res.data.result?.error || "Upload failed.";
        setError(msg);
        showToast(msg, "error");
      }
    }, 1000);
  }

  async function uploadFile(file) {
    if (!file) return;
    if (!centerSelected) {
      setError("Please select an exam center before uploading.");
      return;
    }
    if (busy) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("exam_center_id", examCenterId);
      await api.post("/admin/students/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      pollStatus(0);
    } catch (err) {
      setBusy(false);
      const msg = err.response?.data?.detail || "Upload failed.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      // Allow choosing the same file again (e.g. after fixing it).
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const dropzoneTitle = busy
    ? "Processing the file... (a large PDF can take about a minute — you can leave this page)"
    : centerSelected
      ? "Drag & drop your .xlsx, .csv, .pdf, or .docx file here, or click to browse"
      : "Select an exam center above first";

  function openPicker() {
    if (centerSelected && !busy) inputRef.current?.click();
  }

  return (
    <CollapsibleCard title="Upload Student Excel Sheet" icon="upload">
      <div className="upload-layout">
        <div className="upload-main">
          <div className="center-select-row">
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
            <AddExamCenterButton
              onAdded={async (center) => {
                onCentersChanged && (await onCentersChanged());
                setExamCenterId(String(center.id));
              }}
            />
          </div>

          <div
            className={`dropzone ${dragOver ? "dropzone-active" : ""} ${!centerSelected || busy ? "dropzone-disabled" : ""} ${busy ? "dropzone-busy" : ""}`}
            role="button"
            tabIndex={centerSelected && !busy ? 0 : -1}
            aria-disabled={!centerSelected || busy}
            aria-label={dropzoneTitle}
            onClick={openPicker}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openPicker();
              }
            }}
            onDragOver={(e) => {
              e.preventDefault();
              if (centerSelected) setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (centerSelected && !busy) uploadFile(e.dataTransfer.files[0]);
            }}
          >
            <span className="dropzone-icon" aria-hidden="true">
              {busy ? <span className="spinner" /> : <Icon name={centerSelected ? "upload" : "building"} size={26} />}
            </span>
            <span className="dropzone-title">{dropzoneTitle}</span>
            {busy ? (
              <span className="job-progress" aria-hidden="true" />
            ) : (
              <span className="dropzone-formats" aria-hidden="true">
                <span>.xlsx</span>
                <span>.xlsm</span>
                <span>.csv</span>
                <span>.pdf</span>
                <span>.docx</span>
              </span>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xlsm,.csv,.pdf,.docx"
              style={{ display: "none" }}
              onChange={(e) => uploadFile(e.target.files[0])}
            />
          </div>

          {error && (
            <div className="error-banner" role="alert">
              <Icon name="alert" size={18} />
              <span>{error}</span>
            </div>
          )}
        </div>

        <aside className="upload-guide" aria-label="How uploading works">
          <h3>How uploading works</h3>
          <ol className="guide-list">
            <li>Accepts .xlsx, .xlsm, .csv, .pdf, or .docx (a table with the same columns).</li>
            <li>Columns expected: Student Name, Email, Mobile Number.</li>
            <li>
              Every student in this sheet is assigned to the exam center selected here — upload one sheet per center.
            </li>
            <li>
              Re-uploading updates existing students by email without duplicating them (including moving them to a
              different center if re-uploaded under a different selection).
            </li>
            <li>If an updated student already has an admit card, it is updated automatically.</li>
            <li>Each mobile number can belong to only one student — students log into the student portal with it.</li>
          </ol>
        </aside>
      </div>

      {result && (
        <div className="upload-result" aria-live="polite">
          <div className="stat-row">
            <span className="badge badge-green">{result.upload.new_students} new</span>
            <span className="badge badge-blue">{result.upload.updated_students} updated</span>
            <span className={`badge ${result.upload.error_count ? "badge-red" : "badge-grey"}`}>
              {result.upload.error_count} skipped
            </span>
            {result.refreshed_tickets.length > 0 && (
              <span className="badge badge-amber">{result.refreshed_tickets.length} admit cards updated</span>
            )}
          </div>

          {result.problems.length > 0 && (
            <div className="upload-section">
              <h3 className="upload-section-title">
                <Icon name="alert" size={18} />
                <span>
                  {result.problems.length} row{result.problems.length === 1 ? "" : "s"} skipped — fix these in your
                  sheet and upload it again
                </span>
              </h3>
              <div className="table-scroll upload-problems">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Mobile</th>
                      <th>Problem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.problems.map((p, i) => (
                      <tr key={i}>
                        <td className="cell-mono" data-label="Row">
                          {p.row}
                        </td>
                        <td data-label="Name">{p.name || <span className="muted">—</span>}</td>
                        <td data-label="Email">{p.email || <span className="muted">—</span>}</td>
                        <td className="cell-mono" data-label="Mobile">
                          {p.mobile || <span className="muted">—</span>}
                        </td>
                        <td className="problem-reason" data-label="Problem">
                          {p.reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.refreshed_tickets.length > 0 && (
            <div className="upload-section">
              <h3 className="upload-section-title">
                <Icon name="refresh" size={18} />
                <span>
                  {result.refreshed_tickets.length} admit card{result.refreshed_tickets.length === 1 ? "" : "s"}{" "}
                  updated with the new details (QR code unchanged)
                </span>
              </h3>
              <ul className="refresh-list">
                {result.refreshed_tickets.map((t, i) => (
                  <li key={i}>
                    <strong>{t.student_name}</strong>: {t.changes.join("; ")}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </CollapsibleCard>
  );
}
