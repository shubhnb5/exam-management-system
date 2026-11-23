import { useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import Pagination from "./Pagination";
import SearchBar from "./SearchBar";
import StudentFormModal from "./StudentFormModal";
import usePagination from "../hooks/usePagination";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";

export default function StudentsTable({ students, centers, onChanged }) {
  const { confirm } = useDialog();
  const { showToast } = useToast();
  const centerName = (id) => centers.find((c) => c.id === id)?.name || id;
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // null = closed, "new" = Add Student, otherwise the student being edited
  const [formStudent, setFormStudent] = useState(null);
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

  function handleSaved(result) {
    const name = result.student.full_name;
    if (formStudent === "new") {
      if (result.ticket_error) showToast(result.ticket_error, "error");
      else if (result.ticket_generated) showToast(`Added ${name} and generated the admit card.`, "success");
      else showToast(`Added ${name}. Generate admit cards when ready.`, "success");
    } else if (result.ticket_changes.length) {
      showToast(`Saved ${name}. Admit card updated (${result.ticket_changes.join("; ")}).`, "success");
    } else {
      showToast(`Saved ${name}.`, "success");
    }
    setFormStudent(null);
    onChanged && onChanged();
  }

  async function deleteOne(s) {
    const ok = await confirm({
      title: "Delete student",
      message: `Delete ${s.full_name} (${s.email})? This also removes their admit card and attendance records and cannot be undone. Their student portal login (if any) is kept, but will show no admit card.`,
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
      message: `Delete ${count} student(s) matching "${search}"? This also removes their admit cards and attendance records and cannot be undone.`,
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
      message: `Delete ALL ${count} students? This also removes their admit cards and attendance records and cannot be undone.`,
      confirmText: "Delete all",
      danger: true,
    });
    if (!ok) return;
    withBusy(() => api.delete("/admin/students"), `Deleted all ${count} students.`);
  }

  return (
    <CollapsibleCard
      title={`Students (${students.length})`}
      icon="students"
      headerExtra={
        <>
          <button type="button" className="btn-small btn-primary" onClick={() => setFormStudent("new")} disabled={busy}>
            <Icon name="plus" size={17} />
            Add Student
          </button>
          <button
            type="button"
            className="btn-small btn-danger"
            onClick={deleteAll}
            disabled={busy || students.length === 0}
          >
            <Icon name="trash" size={16} />
            Delete all
          </button>
        </>
      }
    >
      <SearchBar
        value={search}
        onChange={setSearch}
        placeholder="Search by name, email, mobile, or center..."
        action={
          q && filteredStudents.length > 0 && (
            <button type="button" className="btn-small btn-danger" onClick={deleteMatching} disabled={busy}>
              <Icon name="trash" size={16} />
              Delete matching ({filteredStudents.length})
            </button>
          )
        }
      />

      {error && (
        <div className="error-banner" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Mobile</th>
              <th>Center</th>
              <th>Admit Card</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-state">
                  <div className="empty-state-icon">
                    <Icon name={q ? "search" : "students"} size={24} />
                  </div>
                  {q ? "No students match your search." : "No students yet — upload a sheet or use + Add Student."}
                </td>
              </tr>
            )}
            {pageItems.map((s) => {
              return (
                <tr key={s.id}>
                  <td className="cell-primary" data-label="Name">
                    {s.full_name}
                  </td>
                  <td data-label="Email">{s.email}</td>
                  <td className="cell-mono" data-label="Mobile">
                    {s.mobile_number}
                  </td>
                  <td className="cell-wrap" data-label="Center">
                    {centerName(s.exam_center_id)}
                  </td>
                  <td data-label="Admit Card">
                    <span className={`badge ${s.has_ticket ? "badge-green" : "badge-grey"}`}>
                      {s.has_ticket ? "Ready" : "None"}
                    </span>
                  </td>
                  <td className="cell-actions" data-label="Action">
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
                              })
                              .catch(() => showToast("Could not open admit card.", "error"));
                          }}
                        >
                          <Icon name="eye" size={16} />
                          View PDF
                        </a>
                      )}
                      <button type="button" className="btn-small" onClick={() => setFormStudent(s)} disabled={busy}>
                        <Icon name="edit" size={16} />
                        Edit
                      </button>
                      <button
                        type="button"
                        className="btn-small btn-danger"
                        onClick={() => deleteOne(s)}
                        disabled={busy}
                      >
                        <Icon name="trash" size={16} />
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

      {formStudent && (
        <StudentFormModal
          student={formStudent === "new" ? null : formStudent}
          centers={centers}
          onClose={() => setFormStudent(null)}
          onSaved={handleSaved}
        />
      )}
    </CollapsibleCard>
  );
}
