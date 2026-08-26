export default function StatsPanel({ stats }) {
  if (!stats) return null;
  return (
    <div className="card">
      <h2>Live Attendance — {stats.date}</h2>
      <div className="stats-grid">
        {stats.centers.map((c) => {
          const pct = c.total_students ? Math.round((c.scanned_today / c.total_students) * 100) : 0;
          return (
            <div key={c.exam_center_id} className="stat-card">
              <div className="stat-card-title">{c.exam_center_name}</div>
              <div className="stat-card-number">
                {c.scanned_today} / {c.total_students}
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <div className="muted">{pct}% checked in</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
