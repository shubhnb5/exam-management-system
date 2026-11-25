import axios from "axios";
import { clearSession, getToken } from "./auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://combine-mentor.scoler.co.in/api/",
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A 401 on an authenticated call means the session expired or the password
// was changed elsewhere — send the student back to login. (A 401 from the
// login form itself is just "wrong password" and is handled by that page.)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && getToken() && !url.includes("/student/login")) {
      clearSession();
      window.location.href = "/student/login?expired=1";
    }
    return Promise.reject(error);
  }
);

/** Extracts {fieldErrors, message} from an API error for display. */
export async function parseApiError(err, fallback = "Something went wrong. Please try again.") {
  if (!err.response) {
    return { fieldErrors: {}, message: "Cannot reach the server. Check your internet connection and try again." };
  }
  let data = err.response.data;
  if (data instanceof Blob) {
    try {
      data = JSON.parse(await data.text());
    } catch {
      data = null;
    }
  }
  const detail = data?.detail;
  if (detail && typeof detail === "object" && detail.errors) {
    return { fieldErrors: detail.errors, message: "" };
  }
  if (typeof detail === "string") {
    return { fieldErrors: {}, message: detail };
  }
  return { fieldErrors: {}, message: fallback };
}

export default api;
