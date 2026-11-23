import Icon from "./Icon";

export default function Pagination({ page, totalPages, total, pageSize, onChange }) {
  if (total === 0 || totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="muted pagination-info">
        {start}-{end} of {total}
      </span>
      <div className="pagination-controls">
        <button
          type="button"
          className="btn-small"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <Icon name="chevronLeft" size={16} />
          Prev
        </button>
        <span className="pagination-page">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className="btn-small"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next
          <Icon name="chevronRight" size={16} />
        </button>
      </div>
    </nav>
  );
}
