const fixtures = Object.freeze({
  health: "health",
  login: "auth-login",
  register: "auth-register",
  profile: "profile",
  products: "products",
  "products-empty": "products-empty",
  "product-created": "product-created",
  "entry-created": "food-entry-created",
  "entry-updated": "food-entry-updated",
  "day-summary": "day-summary",
  "day-empty": "day-summary-empty",
  "day-over-target": "day-summary-over-target",
  streak: "streak",
  "streak-empty": "streak-empty",
  "weight-history": "weight-history",
  "weight-empty": "weight-history-empty",
  "weight-saved": "weight-log-saved",
  "stats-calories": "stats-calories",
  "stats-empty": "stats-calories-empty",
  "error-validation": "error-validation",
  "error-registration": "error-registration",
  "error-login": "error-login",
  "error-unauthorized": "error-unauthorized",
  "error-conflict": "error-conflict",
  "error-not-found": "error-not-found",
  "error-server": "error-server",
});

const routes = Object.freeze({
  "GET /health": { default: "health" },
  "POST /auth/login": { default: "login" },
  "POST /auth/register": { default: "register" },
  "POST /auth/logout": { default: null },
  "GET /profile": { default: "profile" },
  "PATCH /profile": { default: "profile" },
  "GET /products": {
    default: "products",
    empty: "products-empty",
  },
  "POST /products": { default: "product-created" },
  "POST /diary": { default: "entry-created" },
  "PATCH /diary/{id}": { default: "entry-updated" },
  "DELETE /diary/{id}": { default: null },
  "GET /diary": {
    default: "day-summary",
    empty: "day-empty",
    "over-target": "day-over-target",
  },
  "GET /weight": { default: "weight-history", empty: "weight-empty" },
  "POST /weight": { default: "weight-saved" },
  "GET /streak": { default: "streak", empty: "streak-empty" },
  "GET /stats/calories": { default: "stats-calories", empty: "stats-empty" },
});

const errorScenarios = Object.freeze({
  validation: { status: 400, fixture: "error-validation" },
  "registration-validation": { status: 400, fixture: "error-registration" },
  "invalid-credentials": { status: 401, fixture: "error-login" },
  unauthorized: { status: 401, fixture: "error-unauthorized" },
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
  const routePath = pathname.replace(/^\/api(?=\/)/, "")
    .replace(/^\/diary\/[^/]+$/, "/diary/{id}");
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
  const fixture = route[scenario];
  return fixture === null ? null : loadMock(fixture);
}
