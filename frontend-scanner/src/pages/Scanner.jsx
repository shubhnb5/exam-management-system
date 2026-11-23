import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { useNavigate } from "react-router-dom";
import api from "../api";
import BrandSeal from "../components/BrandSeal";
import Icon from "../components/Icon";

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
      } else if (err.response?.status === 401) {
        // Login expired (12h) or the admin revoked this device — not a network
        // problem, so say so and send the teacher back to log in.
        setResult({ kind: "error", message: "Your login has expired. Please log in again.", expired: true });
        resumeTimerRef.current = setTimeout(logout, 2500);
        return;
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
      <header className="scanner-header guilloche">
        <div className="scanner-id">
          <BrandSeal size={36} />
          <div>
            <div className="scanner-name">{fullName}</div>
            <div className="scanner-status">
              <span className="live-dot" aria-hidden="true" />
              Gate Scanner
            </div>
          </div>
        </div>
        <button className="btn-small btn-danger" onClick={logout}>
          <Icon name="logout" size={17} />
          Log out
        </button>
      </header>

      <div className="scanner-stage">
        <div id={READER_ID} className="qr-reader" />
        {!cameraError && (
          <div className="scan-hint" aria-hidden="true">
            <Icon name="qr" size={18} />
            Point the camera at the admit card QR code
          </div>
        )}
        {cameraError && (
          <div className="camera-error" role="alert">
            <Icon name="camera" size={44} />
            {cameraError}
          </div>
        )}
      </div>

      {result && (
        <div className={`result-overlay result-${result.kind}`} onClick={resumeScanning} role="alert">
          {result.kind === "success" && (
            <>
              <div className="result-icon">
                <Icon name="check" size={64} strokeWidth={2.6} />
              </div>
              <div className="result-eyebrow">Checked in</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-details">
                <div className="result-sub">Checked in — {result.centerName}</div>
                <div className="result-sub mono">{result.time}</div>
              </div>
            </>
          )}
          {result.kind === "duplicate" && (
            <>
              <div className="result-icon">
                <Icon name="x" size={64} strokeWidth={2.6} />
              </div>
              <div className="result-eyebrow">ALREADY SCANNED TODAY</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-details">
                <div className="result-sub">
                  {result.center} — {result.teacher} — {result.time}
                </div>
              </div>
            </>
          )}
          {result.kind === "wrong_center" && (
            <>
              <div className="result-icon">
                <Icon name="x" size={64} strokeWidth={2.6} />
              </div>
              <div className="result-eyebrow">WRONG EXAM CENTER</div>
              <div className="result-title">{result.studentName}</div>
              <div className="result-details">
                <div className="result-sub">Assigned to: {result.assignedCenter}</div>
              </div>
            </>
          )}
          {result.kind === "error" && (
            <>
              <div className="result-icon">
                <Icon name="alert" size={58} strokeWidth={2.4} />
              </div>
              <div className="result-eyebrow">Not verified</div>
              <div className="result-title">{result.message}</div>
            </>
          )}
          <div className="result-footer">
            <div className="result-timer" aria-hidden="true">
              <span
                key={`${result.kind}-${result.time || result.message}`}
                style={{ animationDuration: `${result.expired ? 2500 : AUTO_RESUME_MS}ms` }}
              />
            </div>
            <div className="result-tap-hint">
              {result.expired ? "Taking you to the login page…" : "Tap anywhere to scan next"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
