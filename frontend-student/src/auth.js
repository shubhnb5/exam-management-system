// Separate storage keys from the admin/scanner apps: in production all three
// are served from the same domain, so they share one localStorage.
const TOKEN_KEY = "student_token";
const NAME_KEY = "student_name";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveSession(token, fullName) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(NAME_KEY, fullName || "");
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(NAME_KEY);
  } catch {
    // ignore
  }
}
