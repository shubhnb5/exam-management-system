import { useEffect } from "react";

export default function Modal({ title, children, onClose, wide = false }) {
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={`modal-card ${wide ? "modal-card-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        {title && <div className="modal-title">{title}</div>}
        {children}
      </div>
    </div>
  );
}
