export default function SearchBar({ value, onChange, placeholder = "Search...", action }) {
  return (
    <div className="search-bar">
      <input
        type="search"
        className="search-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {action}
    </div>
  );
}
