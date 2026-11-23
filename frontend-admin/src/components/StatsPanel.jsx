import Icon from "./Icon";

const RING_RADIUS = 52;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

// Status colours (same thresholds as before): verdigris / turmeric / vermilion.
const COLOR_GOOD = "#2e9e77";
const COLOR_MID = "#e39a1f";
const COLOR_LOW = "#d9533b";

function pct(scanned, total) {
  const raw = total ? (scanned / total) * 100 : 0;
  return raw > 0 && raw < 1 ? Math.round(raw * 10) / 10 : Math.round(raw);
}

function progressColor(p) {
  if (p >= 70) return COLOR_GOOD;
  if (p >= 30) return COLOR_MID;
  return COLOR_LOW;
}

function statusMeta(p) {
  if (p >= 70) return { label: "Excellent", badgeClass: "badge-green" };
  if (p >= 30) return { label: "Moderate", badgeClass: "badge-amber" };
  return { label: "Low", badgeClass: "badge-red" };
}

export default function StatsPanel({ stats }) {
  if (!stats) return null;

  const totalStudents = stats.centers.reduce((sum, c) => sum + c.total_students, 0);
  const totalScanned = stats.centers.reduce((sum, c) => sum + c.scanned_today, 0);
  const overallPct = pct(totalScanned, totalStudents);
  const ringColor = progressColor(overallPct);
  const ringOffset = RING_CIRCUMFERENCE * (1 - Math.min(overallPct, 100) / 100);

  return (
    <>
      <section className="live-hero guilloche" aria-label={`Live Attendance — ${stats.date}`}>
        <div className="live-hero-head">
          <span className="eyebrow">Live Attendance — {stats.date}</span>
          <span className="live-badge">
            <span className="live-dot" />
            LIVE
          </span>
        </div>

        <div className="attendance-hero">
          <div className="attendance-ring-wrap">
            <svg
              viewBox="0 0 120 120"
              className="attendance-ring"
              role="img"
              aria-label={`${overallPct}% checked in overall`}
            >
              <circle cx="60" cy="60" r={RING_RADIUS} className="attendance-ring-track" />
              <circle
                cx="60"
                cy="60"
                r={RING_RADIUS}
                className="attendance-ring-fill"
                style={{ stroke: ringColor, strokeDasharray: RING_CIRCUMFERENCE, strokeDashoffset: ringOffset }}
              />
            </svg>
            <div className="attendance-ring-label">
              <div className="attendance-ring-pct">{overallPct}%</div>
              <div className="attendance-ring-sub">checked in</div>
            </div>
          </div>
          <div className="attendance-hero-stats">
            <div className="attendance-hero-number">
              {totalScanned} <span className="attendance-hero-of">/ {totalStudents}</span>
            </div>
            <div className="live-hero-caption">students checked in across all centers today</div>
            <div className="stats-legend">
              <span className="stats-legend-item">
                <span className="stats-legend-dot" style={{ background: COLOR_GOOD }} />
                70%+ Excellent
              </span>
              <span className="stats-legend-item">
                <span className="stats-legend-dot" style={{ background: COLOR_MID }} />
                30–69% Moderate
              </span>
              <span className="stats-legend-item">
                <span className="stats-legend-dot" style={{ background: COLOR_LOW }} />
                Below 30% Low
              </span>
            </div>
          </div>
        </div>
      </section>

      <div className="section-heading">
        <h3>Exam centers</h3>
        <span className="muted">
          {stats.centers.length} {stats.centers.length === 1 ? "center" : "centers"} · refreshes every 10 s
        </span>
      </div>

      <div className="stats-grid">
        {stats.centers.map((c) => {
          const p = pct(c.scanned_today, c.total_students);
          const barWidth = p > 0 ? Math.max(p, 2) : 0;
          const color = progressColor(p);
          const status = statusMeta(p);
          const remaining = c.total_students - c.scanned_today;
          return (
            <div key={c.exam_center_id} className="stat-card" style={{ "--accent": color }}>
              <div className="stat-card-header">
                <div className="stat-card-title">
                  <Icon name="building" size={16} className="stat-card-title-icon" />
                  {c.exam_center_name}
                </div>
                <div className="stat-card-pct" style={{ color }}>
                  {p}%
                </div>
              </div>
              <div className="stat-card-number">
                {c.scanned_today} <span className="stat-card-of">/ {c.total_students}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${barWidth}%`, background: color }} />
              </div>
              <div className="stat-card-footer">
                <span className="muted">{remaining > 0 ? `${remaining} remaining` : "All checked in"}</span>
                <span className={`badge ${status.badgeClass}`}>{status.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
