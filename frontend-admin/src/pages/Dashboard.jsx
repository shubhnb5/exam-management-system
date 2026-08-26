import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ExcelUpload from "../components/ExcelUpload";
import TicketActions from "../components/TicketActions";
import StudentsTable from "../components/StudentsTable";
import StatsPanel from "../components/StatsPanel";
import TeachersPanel from "../components/TeachersPanel";
import AttendancePanel from "../components/AttendancePanel";

export default function Dashboard() {
  const [students, setStudents] = useState([]);
  const [centers, setCenters] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [stats, setStats] = useState(null);
  const navigate = useNavigate();

  const refreshAll = useCallback(async () => {
    const [studentsRes, centersRes, teachersRes, statsRes] = await Promise.all([
      api.get("/admin/students"),
      api.get("/admin/exam-centers"),
      api.get("/admin/teachers"),
      api.get("/admin/stats"),
    ]);
    setStudents(studentsRes.data);
    setCenters(centersRes.data);
    setTeachers(teachersRes.data);
    setStats(statsRes.data);
  }, []);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(() => {
      api.get("/admin/stats").then((res) => setStats(res.data));
    }, 10000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    navigate("/login");
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Examflow Admin</h1>
        <button className="btn-small" onClick={logout}>
          Log out
        </button>
      </header>

      <StatsPanel stats={stats} />
      <AttendancePanel />
      {centers.length > 0 && <ExcelUpload centers={centers} onUploaded={refreshAll} />}
      <TicketActions onDone={refreshAll} />
      {centers.length > 0 && <StudentsTable students={students} centers={centers} />}
      {centers.length > 0 && <TeachersPanel teachers={teachers} centers={centers} onChanged={refreshAll} />}
    </div>
  );
}
