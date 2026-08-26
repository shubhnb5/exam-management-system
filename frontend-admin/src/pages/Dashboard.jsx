import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ExcelUpload from "../components/ExcelUpload";
import TicketActions from "../components/TicketActions";
import StudentsTable from "../components/StudentsTable";
import StatsPanel from "../components/StatsPanel";
import TeachersPanel from "../components/TeachersPanel";
import AttendancePanel from "../components/AttendancePanel";
import Sidebar from "../components/Sidebar";
import Spinner from "../components/Spinner";

export default function Dashboard() {
  const [students, setStudents] = useState([]);
  const [centers, setCenters] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [stats, setStats] = useState(null);
  const [active, setActive] = useState("live");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
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
    refreshAll().finally(() => setInitialLoading(false));
    const interval = setInterval(() => {
      api.get("/admin/stats").then((res) => setStats(res.data));
    }, 10000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const hasCenters = centers.length > 0;

  const sections = useMemo(
    () =>
      [
        { id: "live", label: "Live Attendance", show: true },
        { id: "attendance", label: "Attendance", show: true },
        { id: "upload", label: "Upload Students", show: hasCenters },
        { id: "generate", label: "Generate & Send", show: true },
        { id: "students", label: "Students", show: hasCenters },
        { id: "teachers", label: "Teachers", show: hasCenters },
      ].filter((s) => s.show),
    [hasCenters]
  );

  useEffect(() => {
    if (!sections.some((s) => s.id === active)) {
      setActive(sections[0]?.id);
    }
  }, [sections, active]);

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    navigate("/login");
  }

  const activeLabel = sections.find((s) => s.id === active)?.label || "";

  return (
    <div className="app-shell">
      <Sidebar
        sections={sections}
        active={active}
        onSelect={(id) => {
          setActive(id);
          setSidebarOpen(false);
        }}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={logout}
      />

      <div className="dashboard">
        <header className="dashboard-header">
          <div className="header-left">
            <button
              type="button"
              className="btn-small btn-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              ☰
            </button>
            <h1>{activeLabel || "Examflow Admin"}</h1>
          </div>
        </header>

        <main className="dashboard-content">
          {initialLoading ? (
            <Spinner label="Loading dashboard..." />
          ) : (
            <>
              {active === "live" && (stats ? <StatsPanel stats={stats} /> : <Spinner />)}
              {active === "attendance" && <AttendancePanel />}
              {active === "upload" && hasCenters && <ExcelUpload centers={centers} onUploaded={refreshAll} />}
              {active === "generate" && <TicketActions onDone={refreshAll} />}
              {active === "students" && hasCenters && (
                <StudentsTable students={students} centers={centers} onChanged={refreshAll} />
              )}
              {active === "teachers" && hasCenters && (
                <TeachersPanel teachers={teachers} centers={centers} onChanged={refreshAll} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
