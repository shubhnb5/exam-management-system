import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api, { parseApiError } from "../api";
import AuthLayout from "../components/AuthLayout";
import { MobileField, PasswordField } from "../components/Field";
import Icon from "../components/Icon";
import { OtpInput, ResendLink, TestModeNotice, useCountdown } from "../components/Otp";
import { confirmError, mobileError, passwordError } from "../validation";

// Three steps: mobile number -> OTP sent to it -> new password.
export default function ForgotPassword() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState("mobile"); // mobile -> otp -> reset
  const [mobile, setMobile] = useState(location.state?.mobile || "");
  const [otp, setOtp] = useState("");
  const [sendInfo, setSendInfo] = useState(null);
  const [resendAt, setResendAt] = useState(0);
  const [resetToken, setResetToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const secondsLeft = useCountdown(resendAt);

  async function sendOtp(e) {
    e?.preventDefault();
    const problem = mobileError(mobile);
    setErrors({ mobile_number: problem });
    setMessage("");
    if (problem) return;

    setLoading(true);
    try {
      const res = await api.post("/student/forgot-password/send-otp", { mobile_number: mobile });
      setSendInfo(res.data);
      setResendAt(Date.now() + res.data.resend_after_seconds * 1000);
      setOtp("");
      setStep("otp");
    } catch (err) {
      const { fieldErrors, message: msg } = await parseApiError(err);
      if (step === "otp") {
        setErrors({ otp: fieldErrors.mobile_number || fieldErrors.otp || msg });
      } else {
        setErrors(fieldErrors);
        setMessage(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp(e) {
    e.preventDefault();
    if (otp.length !== 6) {
      setErrors({ otp: "Enter the 6-digit OTP." });
      return;
    }
    setErrors({});
    setMessage("");
    setLoading(true);
    try {
      const res = await api.post("/student/forgot-password/verify-otp", { mobile_number: mobile, otp });
      setResetToken(res.data.reset_token);
      setStep("reset");
    } catch (err) {
      const { fieldErrors, message: msg } = await parseApiError(err);
      setErrors({ otp: fieldErrors.otp || fieldErrors.mobile_number || msg });
    } finally {
      setLoading(false);
    }
  }

  async function reset(e) {
    e.preventDefault();
    const next = { new_password: passwordError(password), confirm_password: confirmError(password, confirm) };
    setErrors(next);
    setMessage("");
    if (next.new_password || next.confirm_password) return;

    setLoading(true);
    try {
      await api.post("/student/forgot-password/reset", { reset_token: resetToken, new_password: password });
      navigate("/login", {
        replace: true,
        state: { mobile, notice: "Your password has been reset. Please log in with your new password." },
      });
    } catch (err) {
      const { fieldErrors, message: msg } = await parseApiError(err);
      setErrors(fieldErrors);
      setMessage(msg);
    } finally {
      setLoading(false);
    }
  }

  function startAgain() {
    setStep("mobile");
    setOtp("");
    setErrors({});
    setMessage("");
    setSendInfo(null);
  }

  const footer = (
    <>
      Remembered it? <Link to="/login">Back to login</Link>
    </>
  );

  const stepIndex = { mobile: 1, otp: 2, reset: 3 }[step];
  const stepLabel = { mobile: "Mobile number", otp: "Verify OTP", reset: "New password" }[step];
  const stepper = (
    <div className="stepper">
      <span className="stepper-dots" aria-hidden="true">
        {[1, 2, 3].map((n) => (
          <span key={n} className={n <= stepIndex ? "done" : ""} />
        ))}
      </span>
      <span>
        Step {stepIndex} of 3 · {stepLabel}
      </span>
    </div>
  );

  if (step === "mobile") {
    return (
      <AuthLayout
        title="Forgot password"
        subtitle="Enter your registered mobile number. We'll send you an OTP to reset your password."
        footer={footer}
        beforeForm={stepper}
      >
        <form onSubmit={sendOtp} noValidate>
          <MobileField label="Mobile number" value={mobile} onChange={setMobile} error={errors.mobile_number} autoFocus />
          {message && (
            <div className="banner banner-error" role="alert">
              <Icon name="alert" size={18} />
              <span>{message}</span>
            </div>
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Sending OTP..." : "Send OTP"}
            {!loading && <Icon name="arrowRight" size={19} />}
          </button>
        </form>
      </AuthLayout>
    );
  }

  if (step === "otp") {
    return (
      <AuthLayout
        title="Enter the OTP"
        subtitle={`We sent a 6-digit OTP to +91 ${mobile}. It is valid for 5 minutes.`}
        footer={footer}
        beforeForm={stepper}
      >
        <form onSubmit={verifyOtp} noValidate>
          {sendInfo?.test_mode && <TestModeNotice devOtp={sendInfo.dev_otp} />}
          <OtpInput
            value={otp}
            onChange={(v) => {
              setOtp(v);
              if (errors.otp) setErrors({});
            }}
            error={errors.otp}
            autoFocus
          />
          <div className="otp-actions">
            <ResendLink secondsLeft={secondsLeft} onResend={() => sendOtp()} busy={loading} />
            <button type="button" className="link-button" onClick={startAgain}>
              Change number
            </button>
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Verifying..." : "Verify"}
            {!loading && <Icon name="shield" size={18} />}
          </button>
        </form>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Set a new password"
      subtitle="Mobile number verified. Choose a new password — this page is valid for 10 minutes."
      footer={footer}
      beforeForm={stepper}
    >
      <form onSubmit={reset} noValidate>
        <PasswordField
          label="New password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.new_password}
          autoComplete="new-password"
          maxLength={64}
          hint="At least 8 characters, with a letter and a number."
          autoFocus
        />
        <PasswordField
          label="Confirm new password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={errors.confirm_password}
          autoComplete="new-password"
          maxLength={64}
        />
        {message && (
          <div className="banner banner-error" role="alert">
            <Icon name="alert" size={18} />
            <span>
              {message}{" "}
              {message.includes("expired") && (
                <button type="button" className="link-button" onClick={startAgain}>
                  Start again
                </button>
              )}
            </span>
          </div>
        )}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Saving..." : "Reset password"}
          {!loading && <Icon name="check" size={18} />}
        </button>
      </form>
    </AuthLayout>
  );
}
