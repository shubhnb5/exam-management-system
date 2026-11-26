import { useState } from "react";
import Icon from "./Icon";

// A password <input> with a Show / Hide button inside its right edge, so the
// user can check what they typed. Takes the same props as a normal <input>.
export default function PasswordInput(props) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="password-input">
      <input {...props} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
      >
        <Icon name={visible ? "eyeOff" : "eye"} size={17} />
        <span>{visible ? "Hide" : "Show"}</span>
      </button>
    </span>
  );
}
