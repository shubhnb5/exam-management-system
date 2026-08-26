import CollapsibleCard from "./CollapsibleCard";

export default function StatsPanel({ stats }) {
  if (!stats) return null;
  return (
    <CollapsibleCard title={`Live Attendance — ${stats.date}`}>
      <div className="stats-grid">
        {stats.centers.map((c) => {
          const rawPct = c.total_students ? (c.scanned_today / c.total_students) * 100 : 0;
          const pct =
            rawPct > 0 && rawPct < 1 ? Math.round(rawPct * 10) / 10 : Math.round(rawPct);
          const barWidth = rawPct > 0 ? Math.max(rawPct, 2) : 0;
          return (
            <div key={c.exam_center_id} className="stat-card">
              <div className="stat-card-title">{c.exam_center_name}</div>
              <div className="stat-card-number">
                {c.scanned_today} / {c.total_students}
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${barWidth}%` }} />
              </div>
              <div className="muted">{pct}% checked in</div>
            </div>
          );
        })}
      </div>
    </CollapsibleCard>
  );
}
