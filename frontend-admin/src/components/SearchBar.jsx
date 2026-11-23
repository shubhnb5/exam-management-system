import Icon from "./Icon";

export default function SearchBar({ value, onChange, placeholder = "Search...", action }) {
  return (
    <div className="search-bar">
      <div className="search-field">
        <Icon name="search" size={18} />
        <input
          type="search"
          className="search-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
        />
      </div>
      {action}
    </div>
  );
}
