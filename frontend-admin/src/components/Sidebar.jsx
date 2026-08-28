import { APP_VERSION } from "../version";

export default function Sidebar({ sections, active, onSelect, open, onClose, onLogout }) {
  return (
    <>
      {open && <div className="sidebar-backdrop" onClick={onClose} />}
      <nav className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <span className="sidebar-logo">CM</span>
          Combine Mentor Admin
        </div>
        <ul className="sidebar-menu">
          {sections.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className={`sidebar-link ${active === s.id ? "sidebar-link-active" : ""}`}
                onClick={() => onSelect(s.id)}
              >
                <span className="sidebar-link-icon" aria-hidden="true">
                  {s.icon}
                </span>
                {s.label}
              </button>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          <button type="button" className="btn-small btn-logout sidebar-logout" onClick={onLogout}>
            Log out
          </button>
          <div className="sidebar-version">{APP_VERSION}</div>
        </div>
      </nav>
    </>
  );
}
