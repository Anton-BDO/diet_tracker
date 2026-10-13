import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  fixtureNames,
  loadMock,
  mockRequest,
  MockApiError,
} from "../../frontend/js/mocks/index.js";

const dataRoot = new URL("../../frontend/js/mocks/data/", import.meta.url);

function serveFiles(context) {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url) => {
    const target = new URL(url);
    assert.ok(target.href.startsWith(dataRoot.href), "Загрузка только mock-файлов");
    requests.push(target.href);
    return new Response(await readFile(target), {
      headers: { "Content-Type": "application/json" },
    });
  });
  return requests;
}

test("all advertised fixtures load independently", async (context) => {
  serveFiles(context);
  assert.equal(fixtureNames.length, new Set(fixtureNames).size);
  for (const name of fixtureNames) {
    const first = await loadMock(name);
    const second = await loadMock(name);
    assert.deepEqual(first, second);
    assert.notEqual(first, second);
  }
});

test("supported routes load static responses instead of the backend", async (context) => {
  const requests = serveFiles(context);
  const routes = [
    ["GET", "/health", "health"],
    ["POST", "/auth/login", "login"],
    ["POST", "/auth/register", "register"],
    ["GET", "/user/profile", "profile"],
    ["PUT", "/user/profile", "profile"],
    ["GET", "/products/search?query=кур", "products"],
    ["POST", "/products/custom", "product-created"],
    ["POST", "/food/entry", "entry-created"],
    ["DELETE", "/food/entry?id=demo", "entry-deleted"],
    ["GET", "/api/food/day-summary?date=2026-10-13", "day-summary"],
    ["GET", "/analytics/weekly", "weekly"],
    ["POST", "/weight/log", "weight-saved"],
  ];
  for (const [method, path, fixture] of routes) {
    assert.deepEqual(await mockRequest(path, { method }), await loadMock(fixture));
  }
  assert.equal(requests.length, routes.length * 2);
});

test("empty and over-target scenarios remain separate", async (context) => {
  serveFiles(context);
  const normal = await mockRequest("/food/day-summary");
  const empty = await mockRequest("/food/day-summary", { scenario: "empty" });
  const over = await mockRequest("/food/day-summary", { scenario: "over-target" });
  assert.equal(empty.eaten_calories, 0);
  assert.ok(over.remaining_calories < 0);
  assert.equal(normal.is_success, true);
  normal.meals.breakfast.length = 0;
  assert.equal((await mockRequest("/food/day-summary")).meals.breakfast.length, 1);
  assert.deepEqual(await mockRequest("/products/search", { scenario: "empty" }), []);
  assert.deepEqual(
    (await mockRequest("/analytics/weekly", { scenario: "empty" })).weight_dynamics,
    [],
  );
});

test("API errors retain HTTP status, code, message and field", async (context) => {
  serveFiles(context);
  const scenarios = [
    ["validation", 400, "validation_error"],
    ["unauthorized", 401, "unauthorized"],
    ["forbidden", 403, "forbidden"],
    ["not-found", 404, "not_found"],
    ["conflict", 409, "conflict"],
    ["server-error", 500, "internal_error"],
  ];
  for (const [scenario, status, code] of scenarios) {
    await assert.rejects(
      mockRequest("/food/entry", { method: "POST", scenario }),
      (error) => error instanceof MockApiError
        && error.status === status
        && error.code === code
        && Boolean(error.message),
    );
  }
  await assert.rejects(
    mockRequest("/food/entry", { method: "POST", scenario: "validation" }),
    { field: "grams" },
  );
});

test("unknown fixtures, routes and scenarios never make a request", async (context) => {
  const requests = serveFiles(context);
  await assert.rejects(loadMock("../../profile"), /Неизвестный mock-файл/);
  await assert.rejects(loadMock("toString"), /Неизвестный mock-файл/);
  await assert.rejects(mockRequest("/unknown"), /нет mock-ответа/);
  await assert.rejects(mockRequest("/user/profile", { method: "DELETE" }), /нет mock-ответа/);
  await assert.rejects(mockRequest("/health", { scenario: "empty" }), /нет сценария/);
  assert.equal(requests.length, 0);
});

test("an unavailable fixture is reported as a file-loading error", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response("", { status: 404 }));
  await assert.rejects(loadMock("profile"), /Не удалось загрузить mock-файл profile: 404/);
});
