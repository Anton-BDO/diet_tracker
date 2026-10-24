// Единственная точка, через которую фронт ходит на бэкенд.
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
    profile: () => request("/profile"),
    daySummary: () => request("/day-summary"),
    logout: () => request("/auth/logout", { method: "POST" }),
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
