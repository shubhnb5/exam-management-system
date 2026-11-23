import { useId, useState } from "react";
import Icon from "./Icon";

function FieldMessage({ id, error, hint }) {
  if (error) {
    return (
      <div id={`${id}-err`} className="field-error" role="alert">
        <Icon name="alert" size={15} />
        <span>{error}</span>
      </div>
    );
  }
  return hint ? (
    <div id={`${id}-hint`} className="field-hint">
      {hint}
    </div>
  ) : null;
}

/** Label + input + inline error/hint. Extra props go to the <input>. */
export function TextField({ label, error, hint, optional, prefix, ...inputProps }) {
  const id = useId();
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  return (
    <div className={`field ${error ? "field-invalid" : ""}`}>
      <label htmlFor={id} className="field-label">
        {label}
        {optional && <span className="field-optional"> (optional)</span>}
      </label>
      <div className={`input-wrap ${prefix ? "has-prefix" : ""}`}>
        {prefix && <span className="input-prefix">{prefix}</span>}
        <input id={id} aria-invalid={!!error} aria-describedby={describedBy} {...inputProps} />
      </div>
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  );
}

export function PasswordField({ label, error, hint, ...inputProps }) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  return (
    <div className={`field ${error ? "field-invalid" : ""}`}>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <div className="input-wrap has-suffix">
        <input
          id={id}
          type={visible ? "text" : "password"}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
          {...inputProps}
        />
        <button
          type="button"
          className="input-suffix"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
        >
          <Icon name={visible ? "eyeOff" : "eye"} size={17} />
          {visible ? "Hide" : "Show"}
        </button>
      </div>
      <FieldMessage id={id} error={error} hint={hint} />
    </div>
  );
}

/** `onChange` receives the digits-only value (not an event). */
export function MobileField({ onChange, ...props }) {
  return (
    <TextField
      type="tel"
      inputMode="numeric"
      autoComplete="tel-national"
      maxLength={10}
      placeholder="10-digit mobile number"
      prefix="+91"
      {...props}
      onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 10))}
    />
  );
}
