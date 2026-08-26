import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Login from "./pages/Login";
import Scanner from "./pages/Scanner";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/scan"
          element={
            <ProtectedRoute>
              <Scanner />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/scan" replace />} />
      </Routes>
    </Router>
  );
}
