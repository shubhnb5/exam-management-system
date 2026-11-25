import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://combine-mentor.scoler.co.in/api/",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = (error.config?.url || "").includes("/auth/login");
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("full_name");
      window.location.href = "/scan/login";
    }
    return Promise.reject(error);
  }
);

export default api;
