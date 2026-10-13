const fixtures = Object.freeze({
  health: "health",
  login: "auth-login",
  register: "auth-register",
  profile: "profile",
  products: "products",
  "products-empty": "products-empty",
  "product-created": "product-created",
  "entry-created": "food-entry-created",
  "entry-deleted": "food-entry-deleted",
  "day-summary": "day-summary",
  "day-empty": "day-summary-empty",
  "day-over-target": "day-summary-over-target",
  weekly: "analytics-weekly",
  "weekly-empty": "analytics-empty",
  "weight-saved": "weight-log-saved",
  "error-validation": "error-validation",
  "error-unauthorized": "error-unauthorized",
  "error-conflict": "error-conflict",
  "error-forbidden": "error-forbidden",
  "error-not-found": "error-not-found",
  "error-server": "error-server",
});

const routes = Object.freeze({
  "GET /health": { default: "health" },
  "POST /auth/login": { default: "login" },
  "POST /auth/register": { default: "register" },
  "GET /user/profile": { default: "profile" },
  "PUT /user/profile": { default: "profile" },
  "GET /products/search": {
    default: "products",
    empty: "products-empty",
  },
  "POST /products/custom": { default: "product-created" },
  "POST /food/entry": { default: "entry-created" },
  "DELETE /food/entry": { default: "entry-deleted" },
  "GET /food/day-summary": {
    default: "day-summary",
    empty: "day-empty",
    "over-target": "day-over-target",
  },
  "GET /analytics/weekly": { default: "weekly", empty: "weekly-empty" },
  "POST /weight/log": { default: "weight-saved" },
});

const errorScenarios = Object.freeze({
  validation: { status: 400, fixture: "error-validation" },
  unauthorized: { status: 401, fixture: "error-unauthorized" },
  forbidden: { status: 403, fixture: "error-forbidden" },
  "not-found": { status: 404, fixture: "error-not-found" },
  conflict: { status: 409, fixture: "error-conflict" },
  "server-error": { status: 500, fixture: "error-server" },
});

export const fixtureNames = Object.freeze(Object.keys(fixtures));

export class MockApiError extends Error {
  constructor(status, { code, message, field }) {
    super(message);
    this.name = "MockApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

export async function loadMock(name) {
  if (!Object.hasOwn(fixtures, name)) {
    throw new Error(`Неизвестный mock-файл: ${name}`);
  }
  const url = new URL(`./data/${fixtures[name]}.json`, import.meta.url);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Не удалось загрузить mock-файл ${name}: ${response.status}`);
  }
  return response.json();
}

export async function mockRequest(
  path, { method = "GET", scenario = "default" } = {},
) {
  const pathname = new URL(path, "https://mock.invalid").pathname;
  const routePath = pathname.replace(/^\/api(?=\/)/, "");
  const routeKey = `${method.toUpperCase()} ${routePath}`;
  if (!Object.hasOwn(routes, routeKey)) {
    throw new Error(`Для маршрута ${routeKey} нет mock-ответа`);
  }

  if (Object.hasOwn(errorScenarios, scenario)) {
    const { status, fixture } = errorScenarios[scenario];
    const data = await loadMock(fixture);
    throw new MockApiError(status, data.error);
  }

  const route = routes[routeKey];
  if (!Object.hasOwn(route, scenario)) {
    throw new Error(`Для маршрута ${routeKey} нет сценария ${scenario}`);
  }
  return loadMock(route[scenario]);
}
