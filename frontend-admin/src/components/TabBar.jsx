import Icon from "./Icon";

// Phone-only bottom navigation: the most-used sections plus "More", which
// opens the full section menu (the Sidebar's bottom-sheet presentation).
const PRIMARY = ["live", "attendance", "students", "generate"];

export default function TabBar({ sections, active, onSelect, onMore, moreOpen }) {
  const primary = PRIMARY.map((id) => sections.find((s) => s.id === id)).filter(Boolean);
  const activeInPrimary = primary.some((s) => s.id === active);

  return (
    <nav className="tabbar" aria-label="Quick sections">
      {primary.map((s) => (
        <button
          key={s.id}
          type="button"
          className={`tabbar-item ${active === s.id ? "tabbar-item-active" : ""}`}
          onClick={() => onSelect(s.id)}
          aria-current={active === s.id ? "page" : undefined}
          aria-label={s.label}
        >
          <span className="tabbar-icon">
            <Icon name={s.icon} size={20} />
          </span>
          <span className="tabbar-label">{s.short || s.label}</span>
        </button>
      ))}
      <button
        type="button"
        className={`tabbar-item ${moreOpen || !activeInPrimary ? "tabbar-item-active" : ""}`}
        onClick={onMore}
        aria-haspopup="true"
        aria-expanded={moreOpen}
        aria-label="All sections"
      >
        <span className="tabbar-icon">
          <Icon name="grid" size={19} />
        </span>
        <span className="tabbar-label">More</span>
      </button>
    </nav>
  );
}
