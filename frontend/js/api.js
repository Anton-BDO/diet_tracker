import { mockRequest } from "./mocks/index.js";

const API_BASE = "/api";

export class ApiError extends Error {
  constructor(status, code, message, field) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

export function createApiClient({
  fetchImpl = globalThis.fetch,
  storage = globalThis.localStorage,
  mock = false,
  mockScenario = "default",
  onUnauthorized = () => {},
} = {}) {
  const tokenKey = mock ? "mock_token" : "token";

  async function request(path, { method = "GET", body } = {}) {
    try {
      if (mock) {
        const authRequest = path === "/auth/login" || path === "/auth/register";
        return await mockRequest(path, {
          method, body, scenario: authRequest ? mockScenario : "default",
        });
      }
      const headers = { "Content-Type": "application/json" };
      const token = storage?.getItem(tokenKey);
      if (token) headers.Authorization = `Bearer ${token}`;
      const response = await fetchImpl(API_BASE + path, {
        method, headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      let data = null;
      if (response.status !== 204) {
        try {
          data = await response.json();
        } catch {
          throw new ApiError(response.status, "invalid_response",
            "Сервер вернул некорректный ответ. Попробуйте позже");
        }
      }
      if (!response.ok) {
        const error = data?.error ?? {};
        throw new ApiError(response.status, error.code, error.message, error.field);
      }
      return data;
    } catch (error) {
      if (error.status === 401) {
        storage?.removeItem(tokenKey);
        onUnauthorized();
      }
      throw error;
    }
  }

  return {
    request, tokenKey, mock,
    health: () => request("/health"),
    login: body => request("/auth/login", { method: "POST", body }),
    register: body => request("/auth/register", { method: "POST", body }),
    logout: () => request("/auth/logout", { method: "POST" }),
    profile: () => request("/profile"),
    updateProfile: body => request("/profile", { method: "PATCH", body }),
    products: (q) => request(`/products?${new URLSearchParams({
      q: String(q ?? ""),
    })}`),
    createProduct: body => request("/products", { method: "POST", body }),
    daySummary: (date) => request(`/diary?date=${date}`),
    createEntry: body => request("/diary", { method: "POST", body }),
    updateEntry: (id, body) => request(
      `/diary/${encodeURIComponent(id)}`,
      { method: "PATCH", body },
    ),
    deleteEntry: (id) => request(
      `/diary/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),
    weightHistory: ({ from, to } = {}) => {
      const params = new URLSearchParams();
      if (from) params.set("from", from);
      if (to) params.set("to", to);
      const suffix = params.size ? `?${params}` : "";
      return request(`/weight${suffix}`);
    },
    logWeight: body => request("/weight", { method: "POST", body }),
    streak: (today) => {
      const suffix = today ? `?${new URLSearchParams({ today })}` : "";
      return request(`/streak${suffix}`);
    },
    caloriesStats: ({ days, today } = {}) => {
      const params = new URLSearchParams();
      if (days !== undefined) params.set("days", String(days));
      if (today) params.set("today", today);
      const suffix = params.size ? `?${params}` : "";
      return request(`/stats/calories${suffix}`);
    },
  };
}

const query = new URLSearchParams(globalThis.location?.search ?? "");
const mockError = query.get("mock-error");

export const api = createApiClient({
  mock: query.get("mock") === "1",
  mockScenario: ["registration-validation", "invalid-credentials"].includes(mockError)
    ? mockError : "default",
  onUnauthorized: () => globalThis.dispatchEvent?.(new Event("auth:expired")),
});

export const request = api.request;
