import { useEffect } from "react";
import { APP_VERSION } from "../version";
import BrandSeal from "./BrandSeal";
import Icon from "./Icon";

// One navigation component, three presentations (see index.css):
//   phones  — a bottom sheet opened from the tab bar's "More"
//   tablets — a compact rail with short labels
//   laptops — a full sidebar with numbered sections
export default function Sidebar({ sections, active, onSelect, open, onClose, onLogout }) {
  useEffect(() => {
    if (!open) return undefined;
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  return (
    <>
      {open && <div className="sidebar-backdrop" onClick={onClose} />}
      <nav className={`sidebar guilloche ${open ? "sidebar-open" : ""}`} aria-label="Sections">
        <span className="sidebar-grabber" aria-hidden="true" />
        <div className="sidebar-brand">
          <BrandSeal size={42} className="sidebar-logo" />
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">Combine Mentor</span>
            <span className="sidebar-brand-sub">Admin Console</span>
          </div>
        </div>
        <div className="sidebar-eyebrow">Sections</div>
        <ul className="sidebar-menu">
          {sections.map((s, i) => (
            <li key={s.id}>
              <button
                type="button"
                className={`sidebar-link ${active === s.id ? "sidebar-link-active" : ""}`}
                onClick={() => onSelect(s.id)}
                aria-current={active === s.id ? "page" : undefined}
                title={s.label}
              >
                <span className="sidebar-link-icon" aria-hidden="true">
                  <Icon name={s.icon} size={19} />
                </span>
                <span className="sidebar-link-index" aria-hidden="true">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="sidebar-link-label">{s.label}</span>
                <span className="sidebar-link-short" aria-hidden="true">
                  {s.short || s.label}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          <button type="button" className="btn-small btn-logout sidebar-logout" onClick={onLogout}>
            <Icon name="logout" size={18} />
            Log out
          </button>
          <div className="sidebar-version">{APP_VERSION}</div>
        </div>
      </nav>
    </>
  );
}
