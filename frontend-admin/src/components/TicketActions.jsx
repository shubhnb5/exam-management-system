import { useEffect, useRef, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import { useToast } from "./ToastProvider";

const POLL_MS = 2000;

export default function TicketActions({ onDone }) {
  const { showToast } = useToast();
  const [genBusy, setGenBusy] = useState(false);
  const [genResult, setGenResult] = useState(null);
  const [error, setError] = useState("");
  const timerRef = useRef(null);

  useEffect(() => {
    // In case a job was already running from a previous page load, pick up its status.
    api.get("/admin/tickets/generate/status").then((res) => {
      if (res.data.status === "running") {
        setGenBusy(true);
        pollGenerate();
      }
    });
    return () => clearTimeout(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pollGenerate() {
    timerRef.current = setTimeout(async () => {
      const res = await api.get("/admin/tickets/generate/status");
      if (res.data.status === "running") {
        pollGenerate();
      } else {
        setGenBusy(false);
        if (res.data.status === "done") {
          setGenResult(res.data.result);
          const r = res.data.result;
          showToast(
            `Admit cards generated: ${r.generated} new, ${r.skipped_existing} already existed${
              r.failed?.length ? `, ${r.failed.length} failed` : ""
            }.`,
            r.failed?.length ? "error" : "success"
          );
        }
        if (res.data.status === "error") {
          setError(`Admit card generation failed: ${res.data.result?.error}`);
          showToast(`Admit card generation failed: ${res.data.result?.error}`, "error");
        }
        onDone && onDone();
      }
    }, POLL_MS);
  }

  async function generate() {
    setError("");
    setGenBusy(true);
    setGenResult(null);
    try {
      await api.post("/admin/tickets/generate");
      pollGenerate();
    } catch (err) {
      setGenBusy(false);
      const msg = err.response?.data?.detail || "Could not start admit card generation.";
      setError(msg);
      showToast(msg, "error");
    }
  }

  return (
    <CollapsibleCard title="Generate Admit Cards" icon="ticket">
      <div className="generate-hero">
        <div className="generate-copy">
          <p>
            Generates an admit card for every uploaded student who doesn't have one yet (all exam centers). As soon as
            a card is generated, the student can download it from the student portal by logging in with their mobile
            number. With hundreds of students this can take a while — it runs in the background, so it's safe to leave
            this page and come back; the status here will pick back up.
          </p>
          <div className="generate-steps" aria-hidden="true">
            <span>
              <Icon name="students" size={16} />
              Uploaded students
            </span>
            <span>
              <Icon name="ticket" size={16} />
              Admit card + QR
            </span>
            <span>
              <Icon name="download" size={16} />
              Student portal
            </span>
          </div>
        </div>
        <div className="generate-action">
          <div className="button-row">
            <button className="btn-lg" onClick={generate} disabled={genBusy}>
              {genBusy ? <span className="spinner spinner-on-dark" aria-hidden="true" /> : <Icon name="ticket" size={19} />}
              {genBusy ? "Generating..." : "Generate Admit Cards"}
            </button>
          </div>
          {genBusy && (
            <div className="generate-status" aria-live="polite">
              <span className="job-progress" aria-hidden="true" />
              <span>Working in the background…</span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      )}

      {genResult && (
        <div className="upload-result" aria-live="polite">
          <div className="stat-row">
            <span className="badge badge-green">{genResult.generated} generated</span>
            <span className="badge badge-blue">{genResult.skipped_existing} already had admit cards</span>
            {genResult.failed.length > 0 && <span className="badge badge-red">{genResult.failed.length} failed</span>}
          </div>
        </div>
      )}
    </CollapsibleCard>
  );
}
