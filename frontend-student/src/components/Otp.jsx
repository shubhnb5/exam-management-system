import { useEffect, useId, useState } from "react";
import Icon from "./Icon";

/** Seconds remaining until `until` (a ms timestamp); re-renders every second. */
export function useCountdown(until) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!until || until <= Date.now()) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [until]);
  // `now` only refreshes on the interval tick, so never let it lag behind the
  // real clock (it was captured when the page first rendered).
  const current = Math.max(now, Date.now());
  return until ? Math.max(0, Math.ceil((until - current) / 1000)) : 0;
}

export function formatSeconds(s) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** 6-digit OTP box. `onChange` receives digits only. */
export function OtpInput({ value, onChange, error, label = "Enter OTP", autoFocus, disabled }) {
  const id = useId();
  return (
    <div className={`field ${error ? "field-invalid" : ""}`}>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <div className="input-wrap otp-wrap">
        <input
          id={id}
          className="otp-input"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="••••••"
          value={value}
          disabled={disabled}
          autoFocus={autoFocus}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : undefined}
          onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
        />
      </div>
      {error && (
        <div id={`${id}-err`} className="field-error" role="alert">
          <Icon name="alert" size={15} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

/** Shown while the backend runs in OTP test mode (no real SMS is sent). */
export function TestModeNotice({ devOtp }) {
  return (
    <div className="banner banner-test" role="status">
      <Icon name="info" size={18} />
      <span>
        <strong>Test mode — no SMS was sent.</strong>
        {devOtp ? (
          <>
            {" "}
            Your OTP is <span className="mono-strong">{devOtp}</span>
          </>
        ) : (
          " The OTP is in the server log."
        )}
      </span>
    </div>
  );
}

/** "Resend OTP" link with a countdown until it's allowed. */
export function ResendLink({ secondsLeft, onResend, busy }) {
  if (secondsLeft > 0) {
    return <span className="resend-wait">Resend OTP in {formatSeconds(secondsLeft)}</span>;
  }
  return (
    <button type="button" className="link-button" onClick={onResend} disabled={busy}>
      {busy ? "Sending..." : "Resend OTP"}
    </button>
  );
}
