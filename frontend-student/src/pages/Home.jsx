import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api, { parseApiError } from "../api";
import { clearSession } from "../auth";
import BrandSeal from "../components/BrandSeal";
import Icon from "../components/Icon";
import { APP_VERSION } from "../version";

const GENDER_LABEL = { male: "Male", female: "Female", other: "Other" };

function formatDate(iso) {
  return iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "";
}

function absoluteApiUrl(path) {
  // baseURL is "/api" in production (same domain) or a full URL.
  return new URL(`${api.defaults.baseURL.replace(/\/$/, "")}${path}`, window.location.href).toString();
}

function AdmitCard({ card, onDownload, downloading, downloadError }) {
  if (card.status === "available") {
    const lastUpdated = card.updated_at || card.generated_at;
    return (
      <section className="ticket" aria-label="Admit Card">
        <div className="ticket-head guilloche">
          <div className="ticket-head-row">
            <h2>
              <Icon name="ticket" size={22} />
              Admit Card
            </h2>
            <span className="pill pill-green">Available</span>
          </div>
          <div className="eyebrow ticket-center-label">Exam centre</div>
          <div className="ticket-center">{card.exam_center_name}</div>
        </div>
        <div className="ticket-perf" aria-hidden="true" />
        <div className="ticket-body">
          <div className="ticket-meta">
            <dl>
              <dt>{card.updated_at ? "Last updated" : "Generated on"}</dt>
              <dd>{formatDate(lastUpdated)}</dd>
            </dl>
            <div className="seal" aria-hidden="true">
              ISSUED
              <br />
              CMO
            </div>
          </div>
          {card.updated_at && (
            <p className="note-update">
              <Icon name="refresh" size={17} />
              <span>
                Your admit card was updated after it was first issued. If you downloaded it before, please download it
                again.
              </span>
            </p>
          )}
          <button type="button" className="btn-primary btn-download" onClick={onDownload} disabled={downloading}>
            {downloading ? (
              <>
                <span className="spinner spinner-light" aria-hidden="true" />
                Preparing download...
              </>
            ) : (
              <>
                <Icon name="download" size={20} />
                Download Admit Card
              </>
            )}
          </button>
          {downloadError && (
            <div className="banner banner-error" role="alert">
              <Icon name="alert" size={18} />
              <span>{downloadError}</span>
            </div>
          )}
          <p className="note">Print the admit card and bring it to the exam centre. Keep the QR code clean and visible.</p>
        </div>
      </section>
    );
  }

  const notGenerated = card.status === "not_generated";
  return (
    <section className="ticket ticket-pending" aria-label="Admit Card">
      <div className="ticket-head guilloche">
        <div className="ticket-head-row">
          <h2>
            <Icon name="ticket" size={22} />
            Admit Card
          </h2>
          <span className="pill pill-amber">Not available</span>
        </div>
      </div>
      <div className="ticket-perf" aria-hidden="true" />
      <div className="ticket-body">
        <div className="empty-card">
          <div className="seal seal-pending" aria-hidden="true">
            NOT YET
            <br />
            ISSUED
          </div>
          <div>
            <p className="empty-card-title">Your admit card is not available yet.</p>
            <p className="empty-card-text">
              {notGenerated
                ? "Your admit card has not been generated yet. Please check again later, or contact the admin."
                : "We could not find an exam registration for your mobile number. Please contact the admin and make sure they have your correct mobile number."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const location = useLocation();
  const [profile, setProfile] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const res = await api.get("/student/me");
      setProfile(res.data);
    } catch (err) {
      setLoadError((await parseApiError(err, "Could not load your details.")).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function logout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  async function download() {
    setDownloading(true);
    setDownloadError("");
    try {
      // Get a short-lived link and let the browser open it normally. Unlike a
      // JavaScript (blob) download, this also works inside WhatsApp /
      // Instagram / Gmail in-app browsers and on older phones. The server
      // sends it as an attachment, so the student stays on this page.
      const res = await api.post("/student/admit-card/link");
      window.location.assign(absoluteApiUrl(res.data.path));
    } catch (err) {
      setDownloadError((await parseApiError(err, "Download failed. Please try again.")).message);
      load(); // status may have changed (e.g. card removed by admin)
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="home-page">
      <header className="topbar">
        <div className="topbar-brand">
          <BrandSeal size={34} />
          <div>
            <div className="brand-name">Combine Mentor</div>
            <div className="brand-sub">Student Portal</div>
          </div>
        </div>
        <button type="button" className="btn-ghost" onClick={logout}>
          <Icon name="logout" size={17} />
          Log out
        </button>
      </header>

      <section className="home-hero guilloche">
        <div className="home-hero-inner greeting">
          {profile && location.state?.welcome && (
            <div className="banner banner-success" role="status">
              <Icon name="checkCircle" size={18} />
              <span>Your account has been created.</span>
            </div>
          )}
          <span className="eyebrow">Your examination pass</span>
          <h1>{profile ? `Hello, ${profile.first_name}!` : "Hello!"}</h1>
        </div>
      </section>

      <main className="home-content">
        {loadError && (
          <div className="banner banner-error" role="alert">
            <Icon name="alert" size={18} />
            <span>
              {loadError}{" "}
              <button type="button" className="link-button" onClick={load}>
                Retry
              </button>
            </span>
          </div>
        )}

        {!profile && !loadError && (
          <div className="loading">
            <span className="spinner" aria-hidden="true" />
            Loading your details...
          </div>
        )}

        {profile && (
          <div className="home-grid">
            <AdmitCard
              card={profile.admit_card}
              onDownload={download}
              downloading={downloading}
              downloadError={downloadError}
            />

            <div className="home-side">
              <section className="panel">
                <div className="panel-head">
                  <h2>
                    <span className="panel-icon" aria-hidden="true">
                      <Icon name="user" size={18} />
                    </span>
                    My Profile
                  </h2>
                </div>
                <dl className="details">
                  <div>
                    <dt>Name</dt>
                    <dd>{profile.full_name}</dd>
                  </div>
                  <div>
                    <dt>Mobile number</dt>
                    <dd className="mono">+91 {profile.mobile_number}</dd>
                  </div>
                  <div>
                    <dt>Gmail ID</dt>
                    <dd className="break">{profile.email}</dd>
                  </div>
                  <div>
                    <dt>Gender</dt>
                    <dd>{GENDER_LABEL[profile.gender] || profile.gender}</dd>
                  </div>
                </dl>
              </section>
            </div>
          </div>
        )}
      </main>
      <div className="app-version">{APP_VERSION}</div>
    </div>
  );
}
