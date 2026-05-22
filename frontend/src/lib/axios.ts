import axios from "axios";
import { logout } from "../utils/authUtils";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request interceptor: attach the access token to every request ──────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// ── Response interceptor: auto-logout on 401 (expired / invalid token) ─────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is expired, invalid, or has been revoked on the server.
      // Clear credentials and send the user back to the login page.
      logout();
    }
    return Promise.reject(error);
  },
);

export default api;
