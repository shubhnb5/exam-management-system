import { useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Pagination from "./Pagination";
import SearchBar from "./SearchBar";
import usePagination from "../hooks/usePagination";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";

const STATUS_LABEL = {
  sent: { text: "Sent", cls: "badge-green" },
  failed: { text: "Failed", cls: "badge-red" },
  pending: { text: "Pending", cls: "badge-blue" },
};

export default function StudentsTable({ students, centers, onChanged }) {
  const { confirm } = useDialog();
  const { showToast } = useToast();
  const centerName = (id) => centers.find((c) => c.id === id)?.name || id;
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const q = search.trim().toLowerCase();
  const filteredStudents = students.filter((s) => {
    if (!q) return true;
    return (
      s.full_name?.toLowerCase().includes(q) ||
      s.email?.toLowerCase().includes(q) ||
      s.mobile_number?.toLowerCase().includes(q) ||
      centerName(s.exam_center_id)?.toLowerCase().includes(q)
    );
  });
  const { page, setPage, totalPages, pageItems, pageSize, total } = usePagination(
    filteredStudents,
    10,
    q
  );

  async function withBusy(fn, successMessage) {
    setError("");
    setBusy(true);
    try {
      await fn();
      showToast(successMessage, "success");
      onChanged && onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not delete student(s).";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  async function deleteOne(s) {
    const ok = await confirm({
      title: "Delete student",
      message: `Delete ${s.full_name} (${s.email})? This also removes their hall ticket and email history and cannot be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    withBusy(() => api.delete(`/admin/students/${s.id}`), `Deleted ${s.full_name}.`);
  }

  async function deleteMatching() {
    const count = filteredStudents.length;
    const ok = await confirm({
      title: "Delete matching students",
      message: `Delete ${count} student(s) matching "${search}"? This also removes their hall tickets and email history and cannot be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    withBusy(
      () => api.post("/admin/students/delete", { student_ids: filteredStudents.map((s) => s.id) }),
      `Deleted ${count} student(s).`
    );
  }

  async function deleteAll() {
    const count = students.length;
    const ok = await confirm({
      title: "Delete all students",
      message: `Delete ALL ${count} students? This also removes their hall tickets and email history and cannot be undone.`,
      confirmText: "Delete all",
      danger: true,
    });
    if (!ok) return;
    withBusy(() => api.delete("/admin/students"), `Deleted all ${count} students.`);
  }

  return (
    <CollapsibleCard
      title={`Students (${students.length})`}
      headerExtra={
        <button
          type="button"
          className="btn-small btn-danger"
          onClick={deleteAll}
          disabled={busy || students.length === 0}
        >
          Delete all
        </button>
      }
    >
      <SearchBar
        value={search}
        onChange={setSearch}
        placeholder="Search by name, email, mobile, or center..."
        action={
          q && filteredStudents.length > 0 && (
            <button type="button" className="btn-small btn-danger" onClick={deleteMatching} disabled={busy}>
              Delete matching ({filteredStudents.length})
            </button>
          )
        }
      />

      {error && <div className="error-banner">{error}</div>}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Mobile</th>
              <th>Center</th>
              <th>Ticket</th>
              <th>Email Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((s) => {
              const status = STATUS_LABEL[s.email_status] || { text: "Not sent", cls: "badge-grey" };
              return (
                <tr key={s.id}>
                  <td>{s.full_name}</td>
                  <td>{s.email}</td>
                  <td>{s.mobile_number}</td>
                  <td>{centerName(s.exam_center_id)}</td>
                  <td>
                    <span className={`badge ${s.has_ticket ? "badge-green" : "badge-grey"}`}>
                      {s.has_ticket ? "Ready" : "None"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${status.cls}`}>{status.text}</span>
                  </td>
                  <td>
                    <div className="row-actions">
                      {s.has_ticket && (
                        <a
                          className="btn btn-small"
                          href={`${api.defaults.baseURL}/admin/students/${s.id}/ticket`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => {
                            e.preventDefault();
                            api
                              .get(`/admin/students/${s.id}/ticket`, { responseType: "blob" })
                              .then((res) => {
                                const url = window.URL.createObjectURL(res.data);
                                window.open(url, "_blank");
                              });
                          }}
                        >
                          View PDF
                        </a>
                      )}
                      <button
                        type="button"
                        className="btn-small btn-danger"
                        onClick={() => deleteOne(s)}
                        disabled={busy}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onChange={setPage} />
    </CollapsibleCard>
  );
}
