import { useEffect, useRef, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import { useToast } from "./ToastProvider";

const POLL_MS = 2000;

export default function TicketActions({ onDone }) {
  const { showToast } = useToast();
  const [genBusy, setGenBusy] = useState(false);
  const [emailBusy, setEmailBusy] = useState(false);
  const [genResult, setGenResult] = useState(null);
  const [emailResult, setEmailResult] = useState(null);
  const [error, setError] = useState("");
  const timersRef = useRef({});

  useEffect(() => {
    // In case a job was already running from a previous page load, pick up its status.
    api.get("/admin/tickets/generate/status").then((res) => {
      if (res.data.status === "running") {
        setGenBusy(true);
        pollGenerate();
      }
    });
    api.get("/admin/tickets/send-emails/status").then((res) => {
      if (res.data.status === "running") {
        setEmailBusy(true);
        pollSendEmails();
      }
    });
    return () => {
      clearTimeout(timersRef.current.gen);
      clearTimeout(timersRef.current.email);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pollGenerate() {
    timersRef.current.gen = setTimeout(async () => {
      const res = await api.get("/admin/tickets/generate/status");
      if (res.data.status === "running") {
        pollGenerate();
      } else {
        setGenBusy(false);
        if (res.data.status === "done") {
          setGenResult(res.data.result);
          const r = res.data.result;
          showToast(
            `Hall tickets generated: ${r.generated} new, ${r.skipped_existing} already existed${
              r.failed?.length ? `, ${r.failed.length} failed` : ""
            }.`,
            r.failed?.length ? "error" : "success"
          );
        }
        if (res.data.status === "error") {
          setError(`Ticket generation failed: ${res.data.result?.error}`);
          showToast(`Ticket generation failed: ${res.data.result?.error}`, "error");
        }
        onDone && onDone();
      }
    }, POLL_MS);
  }

  function pollSendEmails() {
    timersRef.current.email = setTimeout(async () => {
      const res = await api.get("/admin/tickets/send-emails/status");
      if (res.data.status === "running") {
        pollSendEmails();
      } else {
        setEmailBusy(false);
        if (res.data.status === "done") {
          setEmailResult(res.data.result);
          const r = res.data.result;
          showToast(
            `Emails sent: ${r.sent} sent${r.failed ? `, ${r.failed} failed` : ""}.`,
            r.failed ? "error" : "success"
          );
        }
        if (res.data.status === "error") {
          setError(`Email sending failed: ${res.data.result?.error}`);
          showToast(`Email sending failed: ${res.data.result?.error}`, "error");
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
      const msg = err.response?.data?.detail || "Could not start ticket generation.";
      setError(msg);
      showToast(msg, "error");
    }
  }

  async function sendEmails() {
    setError("");
    setEmailBusy(true);
    setEmailResult(null);
    try {
      await api.post("/admin/tickets/send-emails");
      pollSendEmails();
    } catch (err) {
      setEmailBusy(false);
      const msg = err.response?.data?.detail || "Could not start email sending.";
      setError(msg);
      showToast(msg, "error");
    }
  }

  return (
    <CollapsibleCard title="Generate & Send" accent="#16a34a" icon="🎫">
      <p className="muted">
        With hundreds of students this can take a while — it runs in the background, so it's safe to leave this page
        and come back; the status here will pick back up.
      </p>
      <div className="button-row">
        <button onClick={generate} disabled={genBusy}>
          {genBusy ? "Generating..." : "Generate Hall Tickets"}
        </button>
        <button onClick={sendEmails} disabled={emailBusy}>
          {emailBusy ? "Sending..." : "Send Emails"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {genResult && (
        <div className="stat-row">
          <span className="badge badge-green">{genResult.generated} generated</span>
          <span className="badge badge-blue">{genResult.skipped_existing} already had tickets</span>
          {genResult.failed.length > 0 && <span className="badge badge-red">{genResult.failed.length} failed</span>}
        </div>
      )}

      {emailResult && (
        <div className="stat-row">
          <span className="badge badge-green">{emailResult.sent} sent</span>
          <span className="badge badge-red">{emailResult.failed} failed</span>
        </div>
      )}
    </CollapsibleCard>
  );
}
