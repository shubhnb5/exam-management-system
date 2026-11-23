// Client-side checks mirror backend/app/validators.py so students get
// instant feedback; the server re-validates everything regardless.

const NAME_RE = /^[\p{L}\p{M} .'-]+$/u;
const HAS_LETTER_RE = /\p{L}/u;
const GMAIL_RE = /^[a-z0-9][a-z0-9._+-]{0,63}@gmail\.com$/;
const MOBILE_RE = /^[6-9]\d{9}$/;
const AADHAAR_RE = /^[2-9]\d{11}$/;

const VERHOEFF_D = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
];
const VERHOEFF_P = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
];

function verhoeffOk(num) {
  let c = 0;
  [...num].reverse().forEach((ch, i) => {
    c = VERHOEFF_D[c][VERHOEFF_P[i % 8][Number(ch)]];
  });
  return c === 0;
}

export const digitsOnly = (v) => (v || "").replace(/\D/g, "");

export function formatAadhaarInput(v) {
  return digitsOnly(v)
    .slice(0, 12)
    .replace(/(\d{4})(?=\d)/g, "$1 ");
}

export function nameError(value, { required, label }) {
  const v = value.trim();
  if (!v) return required ? `${label} is required.` : "";
  if (v.length > 50) return `${label} must be at most 50 characters.`;
  if (!NAME_RE.test(v) || !HAS_LETTER_RE.test(v)) return `${label} can contain letters only.`;
  return "";
}

export function gmailError(value) {
  const v = value.trim().toLowerCase();
  if (!v) return "Gmail ID is required.";
  if (!GMAIL_RE.test(v)) return "Enter a valid Gmail address ending with @gmail.com.";
  return "";
}

export function mobileError(value) {
  const v = digitsOnly(value);
  if (!v) return "Mobile number is required.";
  if (!MOBILE_RE.test(v)) return "Enter a valid 10-digit mobile number.";
  return "";
}

export function aadhaarError(value) {
  const v = digitsOnly(value);
  if (!v) return "";
  if (!AADHAAR_RE.test(v) || !verhoeffOk(v)) return "Enter a valid 12-digit Aadhaar number, or leave it blank.";
  return "";
}

export function passwordError(value) {
  if (!value) return "Password is required.";
  if (value.length < 8) return "Password must be at least 8 characters.";
  if (value.length > 64) return "Password must be at most 64 characters.";
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return "Password must contain at least one letter and one number.";
  return "";
}

export function confirmError(password, confirm) {
  if (!confirm) return "Please re-enter your password.";
  if (password !== confirm) return "Passwords do not match.";
  return "";
}
