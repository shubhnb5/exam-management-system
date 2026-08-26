import api from "../api";

const STATUS_LABEL = {
  sent: { text: "Sent", cls: "badge-green" },
  failed: { text: "Failed", cls: "badge-red" },
  pending: { text: "Pending", cls: "badge-blue" },
};

export default function StudentsTable({ students, centers }) {
  const centerName = (id) => centers.find((c) => c.id === id)?.name || id;

  return (
    <div className="card">
      <h2>Students ({students.length})</h2>
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => {
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
                    {s.has_ticket && (
                      <a
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
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
