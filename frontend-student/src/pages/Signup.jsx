import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { parseApiError } from "../api";
import { saveSession } from "../auth";
import AuthLayout from "../components/AuthLayout";
import { PasswordField, TextField } from "../components/Field";
import MobileOtpField from "../components/MobileOtpField";
import Icon from "../components/Icon";
import {
  aadhaarError,
  confirmError,
  digitsOnly,
  formatAadhaarInput,
  gmailError,
  mobileError,
  nameError,
  passwordError,
} from "../validation";

const EMPTY = {
  first_name: "",
  middle_name: "",
  last_name: "",
  gender: "",
  mobile_number: "",
  email: "",
  aadhaar_number: "",
  password: "",
  confirm_password: "",
};

const GENDERS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

function validate(f, mobileToken) {
  const mobileProblem = mobileError(f.mobile_number);
  return {
    first_name: nameError(f.first_name, { required: true, label: "First name" }),
    middle_name: nameError(f.middle_name, { required: false, label: "Middle name" }),
    last_name: nameError(f.last_name, { required: true, label: "Last name" }),
    gender: f.gender ? "" : "Please select your gender.",
    mobile_number: mobileProblem || (mobileToken ? "" : "Please verify your mobile number with the OTP first."),
    email: gmailError(f.email),
    aadhaar_number: aadhaarError(f.aadhaar_number),
    password: passwordError(f.password),
    confirm_password: confirmError(f.password, f.confirm_password),
  };
}

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  // Proof from the OTP step that this mobile number belongs to the student.
  const [mobileToken, setMobileToken] = useState(null);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    // Clear a field's error as soon as the student edits it.
    if (errors[field]) setErrors((e) => ({ ...e, [field]: "" }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage("");
    const next = validate(form, mobileToken);
    setErrors(next);
    const firstInvalid = Object.keys(next).find((k) => next[k]);
    if (firstInvalid) {
      document.querySelector(`[data-field="${firstInvalid}"] input`)?.focus();
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/student/signup", {
        first_name: form.first_name.trim(),
        middle_name: form.middle_name.trim() || null,
        last_name: form.last_name.trim(),
        gender: form.gender,
        mobile_number: form.mobile_number,
        email: form.email.trim().toLowerCase(),
        aadhaar_number: digitsOnly(form.aadhaar_number) || null,
        password: form.password,
        mobile_verification_token: mobileToken,
      });
      saveSession(res.data.access_token, res.data.full_name);
      navigate("/home", { replace: true, state: { welcome: true } });
    } catch (err) {
      const { fieldErrors, message: msg } = await parseApiError(err, "Could not create your account. Please try again.");
      setErrors(fieldErrors);
      // e.g. the verification expired: ask for a fresh OTP.
      if (fieldErrors.mobile_number && /verify/i.test(fieldErrors.mobile_number)) setMobileToken(null);
      setMessage(msg || (Object.keys(fieldErrors).length ? "Please correct the highlighted fields." : ""));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Register once, then log in any time to download your admit card."
      footer={
        <>
          Already registered? <Link to="/login">Log in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <fieldset className="form-section">
          <legend className="form-section-title">01 · Your name</legend>
          <div className="form-grid-2">
            <div data-field="first_name">
              <TextField
                label="First name"
                value={form.first_name}
                onChange={(e) => set("first_name", e.target.value)}
                error={errors.first_name}
                autoComplete="given-name"
                maxLength={50}
                autoFocus
              />
            </div>
            <div data-field="middle_name">
              <TextField
                label="Middle name"
                optional
                value={form.middle_name}
                onChange={(e) => set("middle_name", e.target.value)}
                error={errors.middle_name}
                autoComplete="additional-name"
                maxLength={50}
              />
            </div>
            <div data-field="last_name" className="span-2">
              <TextField
                label="Last name"
                value={form.last_name}
                onChange={(e) => set("last_name", e.target.value)}
                error={errors.last_name}
                autoComplete="family-name"
                maxLength={50}
              />
            </div>
          </div>
        </fieldset>

        <fieldset className="form-section">
          <legend className="form-section-title">02 · About you</legend>
          <fieldset className={`field ${errors.gender ? "field-invalid" : ""}`} data-field="gender">
            <legend className="field-label">Gender</legend>
            <div className="segmented" role="radiogroup">
              {GENDERS.map((g) => (
                <label key={g.value} className={`segment ${form.gender === g.value ? "segment-active" : ""}`}>
                  <input
                    type="radio"
                    name="gender"
                    value={g.value}
                    checked={form.gender === g.value}
                    onChange={() => set("gender", g.value)}
                  />
                  {g.label}
                </label>
              ))}
            </div>
            {errors.gender && (
              <div className="field-error" role="alert">
                <Icon name="alert" size={15} />
                <span>{errors.gender}</span>
              </div>
            )}
          </fieldset>
        </fieldset>

        <fieldset className="form-section">
          <legend className="form-section-title">03 · Contact</legend>
          <div data-field="mobile_number">
            <MobileOtpField
              value={form.mobile_number}
              onChange={(v) => set("mobile_number", v)}
              token={mobileToken}
              onVerified={(t) => {
                setMobileToken(t);
                if (t) setErrors((e) => ({ ...e, mobile_number: "" }));
              }}
              error={errors.mobile_number}
              hint="We'll send an OTP to verify it. You will log in with this number — use the same number your institute has on record."
            />
          </div>
          <div data-field="email">
            <TextField
              label="Gmail ID"
              type="email"
              inputMode="email"
              autoComplete="email"
              placeholder="yourname@gmail.com"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              error={errors.email}
              hint="Kept on your profile for our records."
            />
          </div>
        </fieldset>

        <fieldset className="form-section">
          <legend className="form-section-title">04 · Identity</legend>
          <div data-field="aadhaar_number">
            <TextField
              label="Aadhaar number"
              optional
              inputMode="numeric"
              placeholder="1234 5678 9012"
              maxLength={14}
              value={form.aadhaar_number}
              onChange={(e) => set("aadhaar_number", formatAadhaarInput(e.target.value))}
              error={errors.aadhaar_number}
            />
          </div>
        </fieldset>

        <fieldset className="form-section">
          <legend className="form-section-title">05 · Security</legend>
          <div data-field="password">
            <PasswordField
              label="Password"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              error={errors.password}
              autoComplete="new-password"
              maxLength={64}
              hint="At least 8 characters, with a letter and a number."
            />
          </div>
          <div data-field="confirm_password">
            <PasswordField
              label="Confirm password"
              value={form.confirm_password}
              onChange={(e) => set("confirm_password", e.target.value)}
              error={errors.confirm_password}
              autoComplete="new-password"
              maxLength={64}
            />
          </div>
        </fieldset>

        {message && (
          <div className="banner banner-error" role="alert">
            <Icon name="alert" size={18} />
            <span>{message}</span>
          </div>
        )}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Creating account..." : "Create account"}
          {!loading && <Icon name="arrowRight" size={19} />}
        </button>
      </form>
    </AuthLayout>
  );
}
