export default function Spinner({ label = "Loading..." }) {
  return (
    <div className="spinner-row">
      <span className="spinner" aria-hidden="true" />
      {label && <span className="muted">{label}</span>}
    </div>
  );
}
