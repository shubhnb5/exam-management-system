import { useEffect, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
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
    <CollapsibleCard title="Attendance">
      <div className="inline-form">
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
      </div>

      <SearchBar value={search} onChange={setSearch} placeholder="Search by name, email, or center..." />

      {loading && <Spinner />}

      {data && (
        <>
          <div className="stat-row">
            <span className="badge badge-green">{presentCount} present</span>
            <span className="badge badge-red">{rows.length - presentCount} absent</span>
            <span className="badge badge-grey">{rows.length} total</span>
          </div>

          <div className="table-scroll">
            <table>
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
                {pageItems.map((r) => (
                  <tr key={r.student_id}>
                    <td>{r.full_name}</td>
                    <td>{r.email}</td>
                    <td>{r.exam_center_name}</td>
                    <td>
                      <span className={`badge ${r.present ? "badge-green" : "badge-red"}`}>
                        {r.present ? "Present" : "Absent"}
                      </span>
                    </td>
                    <td>{r.scanned_at ? new Date(r.scanned_at).toLocaleTimeString() : "—"}</td>
                    <td>{r.teacher_name || "—"}</td>
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
