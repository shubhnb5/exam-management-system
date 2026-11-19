import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { APP_VERSION } from "../version";
import { useToast } from "../components/ToastProvider";

export default function Login() {
  const { showToast } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);
      const res = await api.post("/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      if (res.data.role !== "admin") {
        setError("This login is for admin accounts only.");
        setLoading(false);
        return;
      }
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("role", res.data.role);
      showToast("Signed in.", "success");
      navigate("/dashboard");
    } catch {
      setError("Invalid username or password.");
      showToast("Invalid username or password.", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="centered-page">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>Combine Mentor Admin</h1>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="error-banner">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
        <div className="login-version">{APP_VERSION}</div>
      </form>
    </div>
  );
}
