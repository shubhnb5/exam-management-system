import { useRef, useState } from "react";
import api, { parseApiError } from "../api";
import { confirmFirebaseOtp, firebaseErrorMessage, isFirebaseError, sendFirebaseOtp } from "../firebasePhone";
import { MobileField } from "./Field";
import Icon from "./Icon";
import { OtpInput, ResendLink, TestModeNotice, useCountdown } from "./Otp";
import { mobileError } from "../validation";

/**
 * Mobile number with OTP verification (signup).
 *   enter -> "Send OTP" -> sent (enter code / resend / change number) -> verified
 * Calls onVerified(token) with the proof token the signup API requires, and
 * onVerified(null) whenever the number is changed.
 */
export default function MobileOtpField({ value, onChange, token, onVerified, error, hint }) {
  const [stage, setStage] = useState("enter"); // enter | sent
  const [otp, setOtp] = useState("");
  const [localError, setLocalError] = useState("");
  const [otpError, setOtpError] = useState("");
  const [busy, setBusy] = useState(false);
  const [resendAt, setResendAt] = useState(0);
  const [sendInfo, setSendInfo] = useState(null); // { test_mode, dev_otp }
  const secondsLeft = useCountdown(resendAt);
  const confirmationRef = useRef(null); // Firebase confirmation handle (firebase channel)
  const recaptchaRef = useRef(null);

  const verified = !!token;
  const shownMobileError = localError || error;

  async function send() {
    const problem = mobileError(value);
    if (problem) {
      setLocalError(problem);
      return;
    }
    setBusy(true);
    setLocalError("");
    setOtpError("");
    try {
      const res = await api.post("/student/signup/send-otp", { mobile_number: value });
      confirmationRef.current = null;
      if (res.data.channel === "firebase") {
        // Backend checks passed; Google Firebase sends the SMS.
        confirmationRef.current = await sendFirebaseOtp(res.data.firebase, value, recaptchaRef.current);
      }
      setStage("sent");
      setOtp("");
      setSendInfo(res.data);
      setResendAt(Date.now() + res.data.resend_after_seconds * 1000);
    } catch (err) {
      if (isFirebaseError(err)) {
        setLocalError(firebaseErrorMessage(err));
      } else {
        const { fieldErrors, message } = await parseApiError(err, "Could not send the OTP. Please try again.");
        setLocalError(fieldErrors.mobile_number || message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    if (otp.length !== 6) {
      setOtpError("Enter the 6-digit OTP.");
      return;
    }
    setBusy(true);
    setOtpError("");
    try {
      let res;
      if (confirmationRef.current) {
        const idToken = await confirmFirebaseOtp(confirmationRef.current, otp);
        res = await api.post("/student/signup/verify-firebase", { mobile_number: value, id_token: idToken });
      } else {
        res = await api.post("/student/signup/verify-otp", { mobile_number: value, otp });
      }
      confirmationRef.current = null;
      onVerified(res.data.mobile_verification_token);
      setStage("enter");
      setSendInfo(null);
    } catch (err) {
      if (isFirebaseError(err)) {
        setOtpError(firebaseErrorMessage(err));
      } else {
        const { fieldErrors, message } = await parseApiError(err, "Could not verify the OTP. Please try again.");
        setOtpError(fieldErrors.otp || fieldErrors.mobile_number || message);
      }
    } finally {
      setBusy(false);
    }
  }

  function changeNumber() {
    confirmationRef.current = null;
    onVerified(null);
    setStage("enter");
    setOtp("");
    setOtpError("");
    setLocalError("");
    setSendInfo(null);
  }

  return (
    <div className="mobile-otp">
      <div ref={recaptchaRef} className="recaptcha-slot" aria-hidden="true" />
      <MobileField
        label="Mobile number"
        value={value}
        onChange={(v) => {
          setLocalError("");
          onChange(v);
        }}
        error={stage === "enter" && !verified ? shownMobileError : ""}
        hint={stage === "enter" && !verified ? hint : ""}
        readOnly={verified || stage === "sent"}
      />

      {verified && (
        <div className="otp-status otp-status-ok">
          <span className="chip-verified">
            <Icon name="checkCircle" size={16} />
            Mobile number verified
          </span>
          <button type="button" className="link-button" onClick={changeNumber}>
            Change number
          </button>
        </div>
      )}

      {!verified && stage === "enter" && (
        <button type="button" className="btn-secondary" onClick={send} disabled={busy}>
          {busy ? "Sending OTP..." : "Send OTP"}
          {!busy && <Icon name="arrowRight" size={17} />}
        </button>
      )}

      {!verified && stage === "sent" && (
        <div className="otp-panel">
          <div className="otp-status">
            <span>
              OTP sent to <span className="mono-strong">+91 {value}</span>
            </span>
            <button type="button" className="link-button" onClick={changeNumber}>
              Change number
            </button>
          </div>
          {sendInfo?.test_mode && <TestModeNotice devOtp={sendInfo.dev_otp} />}
          <OtpInput
            value={otp}
            onChange={(v) => {
              setOtp(v);
              if (otpError) setOtpError("");
            }}
            error={otpError}
            autoFocus
          />
          <div className="otp-actions">
            <button type="button" className="btn-secondary" onClick={verify} disabled={busy}>
              {busy ? "Verifying..." : "Verify OTP"}
            </button>
            <ResendLink secondsLeft={secondsLeft} onResend={send} busy={busy} />
          </div>
          {localError && (
            <div className="field-error" role="alert">
              <Icon name="alert" size={15} />
              <span>{localError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
