import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import api, { parseApiError } from "../api";
import { saveSession } from "../auth";
import AuthLayout from "../components/AuthLayout";
import { MobileField, PasswordField } from "../components/Field";
import Icon from "../components/Icon";
import { mobileError } from "../validation";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const [mobile, setMobile] = useState(location.state?.mobile || "");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const notice = location.state?.notice || (params.get("expired") ? "Your session has ended. Please log in again." : "");

  async function handleSubmit(e) {
    e.preventDefault();
    const next = { mobile_number: mobileError(mobile), password: password ? "" : "Password is required." };
    setErrors(next);
    setMessage("");
    if (next.mobile_number || next.password) return;

    setLoading(true);
    try {
      const res = await api.post("/student/login", { mobile_number: mobile, password });
      saveSession(res.data.access_token, res.data.full_name);
      navigate("/home", { replace: true });
    } catch (err) {
      const { message: msg } = await parseApiError(err, "Could not log in. Please try again.");
      setMessage(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Student Login"
      subtitle="Log in with the mobile number and password you registered with."
      footer={
        <>
          New student? <Link to="/signup">Create an account</Link>
        </>
      }
    >
      {notice && (
        <div className="banner banner-success" role="status">
          <Icon name="checkCircle" size={18} />
          <span>{notice}</span>
        </div>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <MobileField label="Mobile number" value={mobile} onChange={setMobile} error={errors.mobile_number} autoFocus />
        <PasswordField
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
          autoComplete="current-password"
        />
        <div className="form-row-end">
          <Link to="/forgot-password" state={{ mobile }}>
            Forgot password?
          </Link>
        </div>
        {message && (
          <div className="banner banner-error" role="alert">
            <Icon name="alert" size={18} />
            <span>{message}</span>
          </div>
        )}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Logging in..." : "Log in"}
          {!loading && <Icon name="arrowRight" size={19} />}
        </button>
      </form>
    </AuthLayout>
  );
}
