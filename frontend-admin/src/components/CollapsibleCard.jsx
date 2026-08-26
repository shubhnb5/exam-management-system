export default function CollapsibleCard({ title, headerExtra, children }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>{title}</h2>
        {headerExtra && <div className="card-header-actions">{headerExtra}</div>}
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}
