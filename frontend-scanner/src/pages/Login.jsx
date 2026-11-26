import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { APP_VERSION } from "../version";
import BrandLogo from "../components/BrandLogo";
import PasswordInput from "../components/PasswordInput";
import Icon from "../components/Icon";

export default function Login() {
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
      if (res.data.role !== "teacher") {
        setError("This login is for teacher accounts only.");
        setLoading(false);
        return;
      }
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("role", res.data.role);
      localStorage.setItem("full_name", res.data.full_name);
      navigate("/scan");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="centered-page guilloche">
      <div className="scanner-brand">
        <BrandLogo className="scanner-login-logo" />
        <div>
          <div className="scanner-brand-name">
            Scanner
          </div>
          <div className="scanner-brand-sub">Combine Mentor</div>
        </div>
      </div>
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Sign in</h1>
        <p className="login-card-sub">Teacher accounts only. One login per gate device.</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required autoComplete="username" />
        </label>
        <label>
          Password
          <PasswordInput
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
          {!loading && <Icon name="arrowRight" size={19} />}
        </button>
        <div className="login-version">{APP_VERSION}</div>
      </form>
    </div>
  );
}
