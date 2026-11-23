import Icon from "./Icon";

// Standard content panel. `icon` is an Icon name; `description` is optional
// supporting copy shown under the header.
export default function CollapsibleCard({ title, headerExtra, children, icon, description }) {
  return (
    <section className="card panel">
      <div className="card-header">
        <h2>
          {icon && (
            <span className="card-icon" aria-hidden="true">
              <Icon name={icon} size={19} />
            </span>
          )}
          <span>{title}</span>
        </h2>
        {headerExtra && <div className="card-header-actions">{headerExtra}</div>}
      </div>
      <div className="card-body">
        {description && <p className="card-description">{description}</p>}
        {children}
      </div>
    </section>
  );
}
