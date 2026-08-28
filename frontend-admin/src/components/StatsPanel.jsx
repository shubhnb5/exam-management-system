import CollapsibleCard from "./CollapsibleCard";

const RING_RADIUS = 52;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

function pct(scanned, total) {
  const raw = total ? (scanned / total) * 100 : 0;
  return raw > 0 && raw < 1 ? Math.round(raw * 10) / 10 : Math.round(raw);
}

function progressColor(p) {
  if (p >= 70) return "#22c55e";
  if (p >= 30) return "#f59e0b";
  return "#ef4444";
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
    <CollapsibleCard
      title={`Live Attendance — ${stats.date}`}
      accent="#2563eb"
      icon="📡"
      headerExtra={
        <span className="live-badge">
          <span className="live-dot" />
          LIVE
        </span>
      }
    >
      <div className="attendance-hero">
        <div className="attendance-ring-wrap">
          <svg viewBox="0 0 120 120" className="attendance-ring" role="img" aria-label={`${overallPct}% checked in overall`}>
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
          <div className="muted">students checked in across all centers today</div>
        </div>
      </div>

      <div className="stats-legend">
        <span className="stats-legend-item">
          <span className="stats-legend-dot" style={{ background: "#22c55e" }} />
          70%+ Excellent
        </span>
        <span className="stats-legend-item">
          <span className="stats-legend-dot" style={{ background: "#f59e0b" }} />
          30–69% Moderate
        </span>
        <span className="stats-legend-item">
          <span className="stats-legend-dot" style={{ background: "#ef4444" }} />
          Below 30% Low
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
                <div className="stat-card-title">{c.exam_center_name}</div>
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
    </CollapsibleCard>
  );
}
