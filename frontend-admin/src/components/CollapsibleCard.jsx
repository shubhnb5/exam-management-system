export default function CollapsibleCard({ title, headerExtra, children, accent, icon }) {
  return (
    <div className="card" style={accent ? { "--card-accent": accent } : undefined}>
      <div className="card-header">
        <h2>
          {icon && (
            <span className="card-icon" aria-hidden="true">
              {icon}
            </span>
          )}
          {title}
        </h2>
        {headerExtra && <div className="card-header-actions">{headerExtra}</div>}
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}
