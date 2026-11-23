import { useCallback, useEffect, useState } from "react";
import api from "../api";
import CollapsibleCard from "./CollapsibleCard";
import Icon from "./Icon";
import Pagination from "./Pagination";
import SearchBar from "./SearchBar";
import Spinner from "./Spinner";
import usePagination from "../hooks/usePagination";
import { truncate } from "../utils/text";
import { useDialog } from "./DialogProvider";
import { useToast } from "./ToastProvider";

const CARD_STATUS = {
  available: { text: "Available", cls: "badge-green" },
  not_generated: { text: "Not generated", cls: "badge-amber" },
  not_found: { text: "Not in uploaded list", cls: "badge-grey" },
};

const GENDER_LABEL = { male: "Male", female: "Female", other: "Other" };

function formatDate(iso) {
  return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function StudentAccountsPanel() {
  const { confirm } = useDialog();
  const { showToast } = useToast();
  const [accounts, setAccounts] = useState(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/admin/student-accounts");
      setAccounts(res.data);
      setError("");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load student accounts.");
      setAccounts([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const q = search.trim().toLowerCase();
  const filtered = (accounts || []).filter((a) => {
    if (!q) return true;
    return (
      a.full_name.toLowerCase().includes(q) ||
      a.email.toLowerCase().includes(q) ||
      a.mobile_number.includes(q) ||
      (a.exam_center_name || "").toLowerCase().includes(q)
    );
  });
  const { page, setPage, totalPages, pageItems, pageSize, total } = usePagination(filtered, 10, q);

  async function deleteAccount(a) {
    const ok = await confirm({
      title: "Delete student account",
      message: `Delete the portal login of ${a.full_name} (${a.mobile_number})? The uploaded student record, admit card and attendance are NOT affected. The mobile number becomes free to register again.`,
      confirmText: "Delete account",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await api.delete(`/admin/student-accounts/${a.id}`);
      showToast(`Deleted account of ${a.full_name}.`, "success");
      await load();
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not delete account.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <CollapsibleCard
      title={`Student Accounts${accounts ? ` (${accounts.length})` : ""}`}
      icon="idcard"
      headerExtra={
        <button type="button" className="btn-small" onClick={load} disabled={busy}>
          <Icon name="refresh" size={16} />
          Refresh
        </button>
      }
      description="Students who registered on the student portal. A student sees their admit card when their registered mobile number matches an uploaded student who has a generated admit card. If someone registered with the wrong mobile number, delete the account so the right student can register."
    >
      <SearchBar value={search} onChange={setSearch} placeholder="Search by name, Gmail, mobile, or center..." />
      {error && (
        <div className="error-banner" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      )}

      {accounts === null ? (
        <Spinner label="Loading student accounts..." />
      ) : (
        <>
          <div className="table-scroll">
            <table className="data-table data-table-dense">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Mobile</th>
                  <th>Gmail</th>
                  <th>Gender</th>
                  <th>Aadhaar</th>
                  <th>Admit Card</th>
                  <th>Registered</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.length === 0 && (
                  <tr>
                    <td colSpan={8} className="empty-state">
                      <div className="empty-state-icon">
                        <Icon name={q ? "search" : "idcard"} size={24} />
                      </div>
                      {q ? "No accounts match your search." : "No students have registered on the portal yet."}
                    </td>
                  </tr>
                )}
                {pageItems.map((a) => {
                  const card = CARD_STATUS[a.admit_card_status] || CARD_STATUS.not_found;
                  return (
                    <tr key={a.id}>
                      <td className="cell-primary" data-label="Name">
                        {a.full_name}
                      </td>
                      <td className="cell-mono" data-label="Mobile">
                        <div>
                          {a.mobile_number}
                          <div className={`cell-sub verify-flag ${a.mobile_verified ? "verify-ok" : "verify-no"}`}>
                            {a.mobile_verified ? "✓ OTP verified" : "Not verified"}
                          </div>
                        </div>
                      </td>
                      <td data-label="Gmail">{a.email}</td>
                      <td data-label="Gender">{GENDER_LABEL[a.gender] || a.gender}</td>
                      <td className="cell-mono" data-label="Aadhaar">
                        {a.aadhaar_masked || <span className="muted">—</span>}
                      </td>
                      <td className="cell-status" data-label="Admit Card">
                        <div>
                          <span className={`badge ${card.cls}`} title={a.exam_center_name || ""}>
                            {card.text}
                          </span>
                          {a.exam_center_name && (
                            <div className="muted cell-sub" title={a.exam_center_name}>
                              {truncate(a.exam_center_name, 32)}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="cell-mono cell-date" data-label="Registered">
                        {formatDate(a.created_at)}
                      </td>
                      <td className="cell-actions" data-label="Action">
                        <div className="row-actions">
                          <button
                            type="button"
                            className="btn-small btn-danger"
                            onClick={() => deleteAccount(a)}
                            disabled={busy}
                          >
                            <Icon name="trash" size={16} />
                            Delete account
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
        </>
      )}
    </CollapsibleCard>
  );
}
