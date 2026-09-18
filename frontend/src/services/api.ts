import axios, { AxiosError } from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Intercept requests to attach JWT access token if present
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept responses for token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh/`, {
            refresh: refreshToken,
          });
          const newAccess = res.data.access;
          localStorage.setItem("access_token", newAccess);
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          return apiClient(originalRequest);
        } catch (refreshErr) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "#/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// Authentication Services
export const authApi = {
  register: (payload: { email: string; password: string; password_confirm: string; first_name?: string; last_name?: string }) =>
    apiClient.post("/auth/register/", payload).then((r) => r.data),

  login: (payload: { email: string; password: string }) =>
    apiClient.post("/auth/login/", payload).then((r) => r.data),

  getMe: () => apiClient.get("/auth/me/").then((r) => r.data.user || r.data),

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
};

// Policy Services
export const policyApi = {
  list: () => apiClient.get("/policies/").then((r) => r.data.results || r.data),

  get: (id: string) => apiClient.get(`/policies/${id}/`).then((r) => r.data),

  create: (payload: { name: string; provider: string; policy_type: string }) =>
    apiClient.post("/policies/", payload).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/policies/${id}/`).then((r) => r.data),

  uploadDocument: (policyId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post(`/policies/${policyId}/documents/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },

  analyze: (policyId: string) =>
    apiClient.post(`/policies/${policyId}/analyze/`).then((r) => r.data),

  getAnalysis: (policyId: string) =>
    apiClient.get(`/policies/${policyId}/analysis/`).then((r) => r.data),

  getClauses: (policyId: string, category?: string) => {
    const params = category ? { category } : {};
    return apiClient.get(`/policies/${policyId}/clauses/`, { params }).then((r) => r.data.clauses || r.data);
  },

  chat: (policyId: string, question: string, conversationId?: string) =>
    apiClient.post(`/policies/${policyId}/chat/`, { question, conversation_id: conversationId }).then((r) => r.data),
};

