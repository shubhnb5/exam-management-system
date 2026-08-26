import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { useNavigate } from "react-router-dom";
import api from "../api";

const READER_ID = "qr-reader";
const AUTO_RESUME_MS = 3000;

export default function Scanner() {
  const [result, setResult] = useState(null); // { kind: 'success'|'duplicate'|'error', ... }
  const [cameraError, setCameraError] = useState("");
  const qrRef = useRef(null);
  const runningRef = useRef(false);
  const processingRef = useRef(false);
  const resumeTimerRef = useRef(null);
  const navigate = useNavigate();
  const fullName = localStorage.getItem("full_name") || "Teacher";

  function safeStop() {
    // html5-qrcode throws synchronously (not a rejected promise) if stop()
    // is called before start() has actually finished, which happens if the
    // component unmounts (or the user logs out) while the camera is still
    // spinning up — so a plain .catch() on the promise isn't enough here.
    if (!runningRef.current) return;
    try {
      qrRef.current?.stop().catch(() => {});
    } catch {
      // ignore
    } finally {
      runningRef.current = false;
    }
  }

  useEffect(() => {
    const qr = new Html5Qrcode(READER_ID);
    qrRef.current = qr;
    let cancelled = false;

    Html5Qrcode.getCameras()
      .then((cameras) => {
        if (cancelled) return;
        if (!cameras || cameras.length === 0) {
          setCameraError("No camera found on this device.");
          return;
        }
        const backCamera = cameras.find((c) => /back|rear|environment/i.test(c.label)) || cameras[cameras.length - 1];
        return qr
          .start(backCamera.id, { fps: 10, qrbox: { width: 260, height: 260 } }, handleDecoded, () => {})
          .then(() => {
            if (cancelled) {
              qr.stop().catch(() => {});
              return;
            }
            runningRef.current = true;
          });
      })
      .catch((err) => setCameraError("Could not access camera: " + err));

    return () => {
      cancelled = true;
      clearTimeout(resumeTimerRef.current);
      safeStop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleDecoded(decodedText) {
    if (processingRef.current || !runningRef.current) return;
    processingRef.current = true;
    try {
      qrRef.current?.pause(true);
    } catch {
      // ignore — camera may already be paused/stopped
    }

    try {
      const res = await api.post("/scan", { qr_token: decodedText });
      setResult({
        kind: "success",
        studentName: res.data.student_name,
        centerName: res.data.exam_center_name,
        time: new Date(res.data.scanned_at).toLocaleTimeString(),
      });
    } catch (err) {
      if (err.response?.status === 409) {
        const d = err.response.data.detail;
        setResult({
          kind: "duplicate",
          studentName: d.student_name,
          center: d.original_scan_center,
          teacher: d.original_scan_teacher,
          time: new Date(d.original_scan_time).toLocaleTimeString(),
        });
      } else if (err.response?.status === 403) {
        const d = err.response.data.detail;
        setResult({
          kind: "wrong_center",
          studentName: d.student_name,
          assignedCenter: d.assigned_center,
        });
      } else if (err.response?.status === 404) {
        setResult({ kind: "error", message: "QR code not recognized." });
      } else {
        setResult({ kind: "error", message: "Network error — check connection and try again." });
      }
    }

    resumeTimerRef.current = setTimeout(resumeScanning, AUTO_RESUME_MS);
  }

  function resumeScanning() {
    clearTimeout(resumeTimerRef.current);
    setResult(null);
    processingRef.current = false;
    if (runningRef.current) {
      try {
        qrRef.current?.resume();
      } catch {
        // ignore
      }
    }
  }

  function logout() {
    safeStop();
    localStorage.clear();
    navigate("/login");
  }

  return (
    <div className="scanner-page">
      <header className="scanner-header">
        <span>{fullName}</span>
        <button className="btn-small" onClick={logout}>
          Log out
        </button>
      </header>

      <div id={READER_ID} className="qr-reader" />

      {cameraError && <div className="camera-error">{cameraError}</div>}

      {result && (
        <div className={`result-overlay result-${result.kind}`} onClick={resumeScanning}>
          {result.kind === "success" && (
            <>
              <div className="result-icon">&#10003;</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-sub">Checked in — {result.centerName}</div>
              <div className="result-sub">{result.time}</div>
            </>
          )}
          {result.kind === "duplicate" && (
            <>
              <div className="result-icon">&#10007;</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-sub">ALREADY SCANNED TODAY</div>
              <div className="result-sub">
                {result.center} — {result.teacher} — {result.time}
              </div>
            </>
          )}
          {result.kind === "wrong_center" && (
            <>
              <div className="result-icon">&#10007;</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-sub">WRONG EXAM CENTER</div>
              <div className="result-sub">Assigned to: {result.assignedCenter}</div>
            </>
          )}
          {result.kind === "error" && (
            <>
              <div className="result-icon">!</div>
              <div className="result-title">{result.message}</div>
            </>
          )}
          <div className="result-tap-hint">Tap anywhere to scan next</div>
        </div>
      )}
    </div>
  );
}
