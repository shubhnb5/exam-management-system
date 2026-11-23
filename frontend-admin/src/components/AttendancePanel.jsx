import { useEffect, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import Pagination from "./Pagination";
import SearchBar from "./SearchBar";
import Spinner from "./Spinner";
import usePagination from "../hooks/usePagination";

function todayIso() {
  const d = new Date();
  const offset = d.getTimezoneOffset();
  return new Date(d.getTime() - offset * 60000).toISOString().slice(0, 10);
}

export default function AttendancePanel() {
  const [date, setDate] = useState(todayIso());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all"); // all | present | absent
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .get("/admin/attendance", { params: { date } })
      .then((res) => setData(res.data))
      .finally(() => setLoading(false));
  }, [date]);

  const rows = data?.rows || [];
  const presentCount = rows.filter((r) => r.present).length;
  const q = search.trim().toLowerCase();
  const filteredRows = rows.filter((r) => {
    if (filter === "present" && !r.present) return false;
    if (filter === "absent" && r.present) return false;
    if (!q) return true;
    return (
      r.full_name?.toLowerCase().includes(q) ||
      r.email?.toLowerCase().includes(q) ||
      r.exam_center_name?.toLowerCase().includes(q)
    );
  });

  const { page, setPage, totalPages, pageItems, pageSize, total } = usePagination(
    filteredRows,
    10,
    `${date}-${filter}-${q}`
  );

  return (
    <CollapsibleCard
      title="Attendance"
      icon="calendar"
      description="Who was present or absent on any exam date, and which teacher checked them in."
    >
      <div className="toolbar">
        <label className="field-label">
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="field-label">
          Show
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All students</option>
            <option value="present">Present only</option>
            <option value="absent">Absent only</option>
          </select>
        </label>
        <SearchBar value={search} onChange={setSearch} placeholder="Search by name, email, or center..." />
      </div>

      {loading && <Spinner />}

      {data && (
        <>
          <div className="summary-tiles">
            <div className="summary-tile summary-tile-present">
              <span className="summary-tile-value mono">{presentCount}</span>
              <span className="summary-tile-label">present</span>
            </div>
            <div className="summary-tile summary-tile-absent">
              <span className="summary-tile-value mono">{rows.length - presentCount}</span>
              <span className="summary-tile-label">absent</span>
            </div>
            <div className="summary-tile summary-tile-total">
              <span className="summary-tile-value mono">{rows.length}</span>
              <span className="summary-tile-label">total</span>
            </div>
          </div>

          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Center</th>
                  <th>Status</th>
                  <th>Scanned At</th>
                  <th>Scanned By</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty-state">
                      <div className="empty-state-icon">
                        <Icon name="inbox" size={24} />
                      </div>
                      {q ? "No students match your search." : "No students found for this date/filter."}
                    </td>
                  </tr>
                )}
                {pageItems.map((r) => (
                  <tr key={r.student_id}>
                    <td className="cell-primary" data-label="Name">
                      {r.full_name}
                    </td>
                    <td data-label="Email">{r.email}</td>
                    <td data-label="Center">{r.exam_center_name}</td>
                    <td data-label="Status">
                      <span className={`badge ${r.present ? "badge-green" : "badge-red"}`}>
                        {r.present ? "Present" : "Absent"}
                      </span>
                    </td>
                    <td className="cell-mono" data-label="Scanned At">
                      {r.scanned_at ? new Date(r.scanned_at).toLocaleTimeString() : "—"}
                    </td>
                    <td data-label="Scanned By">{r.teacher_name || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onChange={setPage} />
        </>
      )}
    </CollapsibleCard>
  );
}
