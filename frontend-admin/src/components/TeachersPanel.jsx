import { useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import Pagination from "./Pagination";
import SearchBar from "./SearchBar";
import usePagination from "../hooks/usePagination";
import { truncate } from "../utils/text";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";

export default function TeachersPanel({ teachers, centers, onChanged }) {
  const { confirm, promptText } = useDialog();
  const { showToast } = useToast();
  const [form, setForm] = useState({ username: "", password: "", full_name: "", exam_center_id: centers[0]?.id || "" });
  const [error, setError] = useState("");
  const [tableError, setTableError] = useState("");
  const [busy, setBusy] = useState(false);

  const centerName = (id) => centers.find((c) => c.id === id)?.name || id;
  const [search, setSearch] = useState("");
  const q = search.trim().toLowerCase();
  const filteredTeachers = teachers.filter((t) => {
    if (!q) return true;
    return (
      t.username?.toLowerCase().includes(q) ||
      t.full_name?.toLowerCase().includes(q) ||
      centerName(t.exam_center_id)?.toLowerCase().includes(q)
    );
  });
  const { page, setPage, totalPages, pageItems, pageSize, total } = usePagination(
    filteredTeachers,
    10,
    q
  );

  async function createTeacher(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/admin/teachers", { ...form, exam_center_id: Number(form.exam_center_id) });
      showToast(`Added teacher ${form.username}.`, "success");
      setForm({ username: "", password: "", full_name: "", exam_center_id: centers[0]?.id || "" });
      onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not create teacher.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(teacher) {
    setTableError("");
    try {
      await api.patch(`/admin/teachers/${teacher.id}`, { is_active: !teacher.is_active });
      showToast(
        teacher.is_active ? `Revoked ${teacher.username}.` : `Reactivated ${teacher.username}.`,
        "success"
      );
      onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not update teacher.";
      setTableError(msg);
      showToast(msg, "error");
    }
  }

  async function resetPassword(teacher) {
    const newPassword = await promptText({
      title: "Reset password",
      message: `Set a new password for ${teacher.username}.`,
      inputLabel: "New password",
      inputType: "password",
      confirmText: "Save",
    });
    if (!newPassword) return;
    setTableError("");
    try {
      await api.patch(`/admin/teachers/${teacher.id}`, { password: newPassword });
      showToast(`Password reset for ${teacher.username}.`, "success");
      onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not reset password.";
      setTableError(msg);
      showToast(msg, "error");
    }
  }

  async function deleteTeacher(teacher) {
    const ok = await confirm({
      title: "Delete teacher",
      message: `Delete ${teacher.full_name} (${teacher.username})? This cannot be undone.`,
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    setTableError("");
    try {
      await api.delete(`/admin/teachers/${teacher.id}`);
      showToast(`Deleted ${teacher.full_name}.`, "success");
      onChanged();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not delete teacher.";
      setTableError(msg);
      showToast(msg, "error");
    }
  }

  return (
    <CollapsibleCard
      title="Teacher Devices / Accounts"
      icon="teachers"
      description="One login per teacher device at the gate. Revoke a lost device instantly; scan history is kept."
    >
      <SearchBar value={search} onChange={setSearch} placeholder="Search by username, name, or center..." />
      {tableError && (
        <div className="error-banner" role="alert">
          <Icon name="alert" size={18} />
          <span>{tableError}</span>
        </div>
      )}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Full Name</th>
              <th>Center</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  <div className="empty-state-icon">
                    <Icon name={q ? "search" : "teachers"} size={24} />
                  </div>
                  {q ? "No teachers match your search." : "No teacher accounts yet — add one below."}
                </td>
              </tr>
            )}
            {pageItems.map((t) => (
              <tr key={t.id}>
                <td className="cell-primary cell-mono-primary" data-label="Username">
                  {t.username}
                </td>
                <td data-label="Full Name">{t.full_name}</td>
                <td className="cell-wrap" data-label="Center">
                  {centerName(t.exam_center_id)}
                </td>
                <td data-label="Status">
                  <span className={`badge ${t.is_active ? "badge-green" : "badge-red"}`}>
                    {t.is_active ? "Active" : "Revoked"}
                  </span>
                </td>
                <td className="cell-actions" data-label="Action">
                  <div className="row-actions">
                    <button className="btn-small" onClick={() => toggleActive(t)}>
                      <Icon name={t.is_active ? "ban" : "checkCircle"} size={16} />
                      {t.is_active ? "Revoke" : "Reactivate"}
                    </button>
                    <button className="btn-small" onClick={() => resetPassword(t)}>
                      <Icon name="key" size={16} />
                      Reset password
                    </button>
                    <button className="btn-small btn-danger" onClick={() => deleteTeacher(t)}>
                      <Icon name="trash" size={16} />
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination page={page} totalPages={totalPages} total={total} pageSize={pageSize} onChange={setPage} />

      <div className="subsection">
        <h3>
          <span className="card-icon card-icon-sm" aria-hidden="true">
            <Icon name="plus" size={17} />
          </span>
          Add Teacher
        </h3>
        <form className="inline-form" onSubmit={createTeacher}>
          <label className="field-label">
            Username
            <input
              placeholder="Username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
              autoComplete="off"
            />
          </label>
          <label className="field-label">
            Full name
            <input
              placeholder="Full name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </label>
          <label className="field-label">
            Password
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              autoComplete="new-password"
            />
          </label>
          <label className="field-label">
            Exam center
            <select value={form.exam_center_id} onChange={(e) => setForm({ ...form, exam_center_id: e.target.value })}>
              {centers.map((c) => (
                <option key={c.id} value={c.id} title={c.name}>
                  {truncate(c.name)}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy}>
            <Icon name="plus" size={18} />
            {busy ? "Adding..." : "Add"}
          </button>
        </form>
        {error && (
          <div className="error-banner" role="alert">
            <Icon name="alert" size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </CollapsibleCard>
  );
}
