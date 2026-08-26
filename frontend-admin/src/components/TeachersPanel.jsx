import { useState } from "react";
import api from "../api";

export default function TeachersPanel({ teachers, centers, onChanged }) {
  const [form, setForm] = useState({ username: "", password: "", full_name: "", exam_center_id: centers[0]?.id || "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const centerName = (id) => centers.find((c) => c.id === id)?.name || id;

  async function createTeacher(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/admin/teachers", { ...form, exam_center_id: Number(form.exam_center_id) });
      setForm({ username: "", password: "", full_name: "", exam_center_id: centers[0]?.id || "" });
      onChanged();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create teacher.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(teacher) {
    await api.patch(`/admin/teachers/${teacher.id}`, { is_active: !teacher.is_active });
    onChanged();
  }

  async function resetPassword(teacher) {
    const newPassword = window.prompt(`New password for ${teacher.username}:`);
    if (!newPassword) return;
    await api.patch(`/admin/teachers/${teacher.id}`, { password: newPassword });
    onChanged();
  }

  return (
    <div className="card">
      <h2>Teacher Devices / Accounts</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Full Name</th>
              <th>Center</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {teachers.map((t) => (
              <tr key={t.id}>
                <td>{t.username}</td>
                <td>{t.full_name}</td>
                <td>{centerName(t.exam_center_id)}</td>
                <td>
                  <span className={`badge ${t.is_active ? "badge-green" : "badge-red"}`}>
                    {t.is_active ? "Active" : "Revoked"}
                  </span>
                </td>
                <td className="button-row">
                  <button className="btn-small" onClick={() => toggleActive(t)}>
                    {t.is_active ? "Revoke" : "Reactivate"}
                  </button>
                  <button className="btn-small" onClick={() => resetPassword(t)}>
                    Reset password
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Add Teacher</h3>
      <form className="inline-form" onSubmit={createTeacher}>
        <input
          placeholder="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          required
        />
        <input
          placeholder="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <select value={form.exam_center_id} onChange={(e) => setForm({ ...form, exam_center_id: e.target.value })}>
          {centers.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button type="submit" disabled={busy}>
          {busy ? "Adding..." : "Add"}
        </button>
      </form>
      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
