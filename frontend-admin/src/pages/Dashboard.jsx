import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ExcelUpload from "../components/ExcelUpload";
import TicketActions from "../components/TicketActions";
import StudentsTable from "../components/StudentsTable";
import StatsPanel from "../components/StatsPanel";
import TeachersPanel from "../components/TeachersPanel";
import AttendancePanel from "../components/AttendancePanel";
import StudentAccountsPanel from "../components/StudentAccountsPanel";
import Sidebar from "../components/Sidebar";
import TabBar from "../components/TabBar";
import Spinner from "../components/Spinner";
import BrandSeal from "../components/BrandSeal";
import Icon from "../components/Icon";
import { useToast } from "../components/ToastProvider";

function todayLabel() {
  return new Date().toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
}

export default function Dashboard() {
  const { showToast } = useToast();
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
        { id: "live", label: "Live Attendance", short: "Live", icon: "live", show: true },
        { id: "attendance", label: "Attendance", short: "Attendance", icon: "calendar", show: true },
        // Always shown: it's also where new exam centers are added.
        { id: "upload", label: "Upload Students", short: "Upload", icon: "upload", show: true },
        { id: "generate", label: "Generate Admit Cards", short: "Generate", icon: "ticket", show: true },
        { id: "students", label: "Students", short: "Students", icon: "students", show: hasCenters },
        { id: "accounts", label: "Student Accounts", short: "Accounts", icon: "idcard", show: true },
        { id: "teachers", label: "Teachers", short: "Teachers", icon: "teachers", show: hasCenters },
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
    showToast("Logged out.", "success");
    navigate("/login");
  }

  function selectSection(id) {
    setActive(id);
    setSidebarOpen(false);
    window.scrollTo({ top: 0 });
  }

  const activeIndex = sections.findIndex((s) => s.id === active);
  const activeLabel = sections[activeIndex]?.label || "";

  return (
    <div className="app-shell">
      <Sidebar
        sections={sections}
        active={active}
        onSelect={selectSection}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={logout}
      />

      <div className="dashboard">
        <header className="dashboard-header">
          <div className="header-left">
            <span className="header-seal">
              <BrandSeal size={34} />
            </span>
            <div className="header-titles">
              <span className="eyebrow">
                {activeIndex >= 0
                  ? `Section ${String(activeIndex + 1).padStart(2, "0")} / ${String(sections.length).padStart(2, "0")}`
                  : "Admin Console"}
              </span>
              <h1>{activeLabel || "Combine Mentor Admin"}</h1>
            </div>
          </div>
          <div className="header-right">
            <span className="date-chip">
              <Icon name="calendar" size={15} />
              {todayLabel()}
            </span>
          </div>
        </header>

        <main className="dashboard-content">
          {initialLoading ? (
            <Spinner label="Loading dashboard..." />
          ) : (
            <div className="section-stack" key={active}>
              {active === "live" && (stats ? <StatsPanel stats={stats} /> : <Spinner />)}
              {active === "attendance" && <AttendancePanel />}
              {active === "upload" && (
                <ExcelUpload centers={centers} onUploaded={refreshAll} onCentersChanged={refreshAll} />
              )}
              {active === "generate" && <TicketActions onDone={refreshAll} />}
              {active === "students" && hasCenters && (
                <StudentsTable students={students} centers={centers} onChanged={refreshAll} />
              )}
              {active === "accounts" && <StudentAccountsPanel />}
              {active === "teachers" && hasCenters && (
                <TeachersPanel teachers={teachers} centers={centers} onChanged={refreshAll} />
              )}
            </div>
          )}
        </main>
      </div>

      <TabBar
        sections={sections}
        active={active}
        onSelect={selectSection}
        onMore={() => setSidebarOpen((open) => !open)}
        moreOpen={sidebarOpen}
      />
    </div>
  );
}
