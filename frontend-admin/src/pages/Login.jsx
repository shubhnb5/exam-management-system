import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { APP_VERSION } from "../version";
import { useToast } from "../components/ToastProvider";
import BrandSeal from "../components/BrandSeal";
import Icon from "../components/Icon";

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
    <div className="login-page">
      <section className="login-hero guilloche">
        <div className="login-hero-inner">
          <div className="login-brand">
            <BrandSeal size={48} />
            <div>
              <div className="login-brand-name">Combine Mentor</div>
              <div className="login-brand-sub">Admin</div>
            </div>
          </div>
          <h1 className="login-headline">
            Examination <em>Management System</em>
          </h1>
          <p className="login-lede">
            A unified platform for secure and seamless examination administration
          </p>
          <ul className="login-steps">
            <li>
              <span className="step-no" aria-hidden="true">
                <Icon name="students" size={20} />
              </span>
              <strong>Student &amp; centre management</strong>
              <span>Import student lists, maintain records and manage exam centres.</span>
            </li>
            <li>
              <span className="step-no" aria-hidden="true">
                <Icon name="ticket" size={20} />
              </span>
              <strong>Admit card issuance</strong>
              <span>Generate QR-secured admit cards, available to students on the student portal.</span>
            </li>
            <li>
              <span className="step-no" aria-hidden="true">
                <Icon name="live" size={20} />
              </span>
              <strong>Real-time attendance</strong>
              <span>Monitor QR check-ins and attendance across all exam centres.</span>
            </li>
          </ul>
        </div>
        <div className="login-hero-footer">
          © {new Date().getFullYear()} Combine Mentor Official, Pune. All rights reserved.
        </div>
      </section>

      <div className="login-form-wrap">
        <form className="card login-card" onSubmit={handleSubmit}>
          <h2>Sign in</h2>
          <p className="login-card-sub"></p>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && (
            <div className="error-banner" role="alert">
              <Icon name="alert" size={18} />
              <span>{error}</span>
            </div>
          )}
          <button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
            {!loading && <Icon name="arrowRight" size={18} />}
          </button>
          <div className="login-notice">
            <Icon name="lock" size={16} />
            <span>Restricted access. This console is for authorised Combine Mentor administrators only.</span>
          </div>
          <p className="login-help"></p>
          <div className="login-version">{APP_VERSION}</div>
        </form>
      </div>
    </div>
  );
}
