// Единственная точка, через которую фронт ходит на бэкенд.
const API_BASE = "/api";

export class ApiError extends Error {
  constructor(status, code, message, field) {
    super(message);
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

export async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(API_BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = data?.error ?? {};
    throw new ApiError(response.status, error.code, error.message, error.field);
  }
  return data;
}

export const api = {
  health: () => request("/health"),
};
