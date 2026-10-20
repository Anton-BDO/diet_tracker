import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";
import {
  fixtureNames, loadMock, mockRequest, MockApiError,
} from "../../frontend/js/mocks/index.js";

const dataRoot = new URL("../../frontend/js/mocks/data/", import.meta.url);

function serveFiles(context) {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url) => {
    const target = new URL(url);
    assert.ok(target.href.startsWith(dataRoot.href));
    requests.push(target.href);
    return new Response(await readFile(target), {
      headers: { "Content-Type": "application/json" },
    });
  });
  return requests;
}

test("every fixture loads independently and every JSON file is reachable", async (context) => {
  const requests = serveFiles(context);
  assert.equal(fixtureNames.length, new Set(fixtureNames).size);
  for (const name of fixtureNames) {
    const first = await loadMock(name);
    const second = await loadMock(name);
    assert.deepEqual(first, second);
    assert.notEqual(first, second);
  }
  const files = (await readdir(dataRoot)).filter(name => name.endsWith(".json"));
  const loaded = requests.map(url => new URL(url).pathname.split("/").at(-1));
  assert.deepEqual([...new Set(loaded)].sort(), files.sort());
});

test("routes follow the architecture including diary IDs", async (context) => {
  const requests = serveFiles(context);
  const routes = [
    ["GET", "/health", "health"],
    ["POST", "/auth/login", "login"],
    ["POST", "/auth/register", "register"],
    ["GET", "/profile", "profile"],
    ["PATCH", "/profile", "profile"],
    ["GET", "/products?q=кур", "products"],
    ["POST", "/products", "product-created"],
    ["GET", "/api/diary?date=2026-10-20", "day-summary"],
    ["POST", "/diary", "entry-created"],
    ["PATCH", "/api/diary/6521a3b5c9e8d761a2b3c111", "entry-updated"],
    ["GET", "/weight?from=2026-10-14&to=2026-10-20", "weight-history"],
    ["POST", "/weight", "weight-saved"],
    ["GET", "/streak?today=2026-10-20", "streak"],
    ["GET", "/stats/calories?days=7&today=2026-10-20", "stats-calories"],
  ];
  for (const [method, path, fixture] of routes) {
    assert.deepEqual(await mockRequest(path, { method }), await loadMock(fixture));
  }
  assert.equal(requests.length, routes.length * 2);
});

test("204 responses return null without fetching JSON", async (context) => {
  const requests = serveFiles(context);
  assert.equal(await mockRequest("/auth/logout", { method: "POST" }), null);
  assert.equal(await mockRequest("/diary/entry-123", { method: "DELETE" }), null);
  assert.equal(requests.length, 0);
  await assert.rejects(
    mockRequest("/diary/entry-123", { method: "DELETE", scenario: "unauthorized" }),
    { status: 401 },
  );
});

test("empty and over-target examples remain separate", async (context) => {
  serveFiles(context);
  const normal = await mockRequest("/diary");
  const empty = await mockRequest("/diary", { scenario: "empty" });
  const over = await mockRequest("/diary", { scenario: "over-target" });
  assert.equal(empty.totals.kcal, 0);
  assert.ok(over.remaining.kcal < 0);
  assert.equal(normal.is_success, true);
  assert.equal(over.is_success, false);
  normal.entries.length = 0;
  assert.ok((await mockRequest("/diary")).entries.length > 0);
  assert.deepEqual(await mockRequest("/products", { scenario: "empty" }), []);
  assert.deepEqual(await mockRequest("/weight", { scenario: "empty" }), []);
  assert.deepEqual(await mockRequest("/streak", { scenario: "empty" }), {
    current: 0, record: 0,
  });
  const stats = await mockRequest("/stats/calories", { scenario: "empty" });
  assert.equal(stats.days.length, 7);
  assert.ok(stats.days.every(day => day.kcal === 0 && !day.is_success));
});

test("error scenarios preserve status, code, message and field", async (context) => {
  serveFiles(context);
  for (const [scenario, status, code] of [
    ["validation", 400, "validation_error"],
    ["unauthorized", 401, "unauthorized"],
    ["not-found", 404, "not_found"],
    ["conflict", 409, "conflict"],
    ["server-error", 500, "internal_error"],
  ]) {
    await assert.rejects(
      mockRequest("/diary", { method: "POST", scenario }),
      error => error instanceof MockApiError && error.status === status
        && error.code === code && Boolean(error.message),
    );
  }
  await assert.rejects(
    mockRequest("/auth/register", {
      method: "POST", scenario: "registration-validation",
    }),
    { status: 400, field: "height_cm" },
  );
  await assert.rejects(
    mockRequest("/auth/login", { method: "POST", scenario: "invalid-credentials" }),
    { status: 401, field: "email" },
  );
});

test("obsolete routes and unknown scenarios never fetch files", async (context) => {
  const requests = serveFiles(context);
  for (const name of ["../../profile", "toString", "entry-deleted", "weekly"]) {
    await assert.rejects(loadMock(name), /Неизвестный mock-файл/);
  }
  for (const path of ["/unknown", "/user/profile", "/food/day-summary", "/products/search"]) {
    await assert.rejects(mockRequest(path), /нет mock-ответа/);
  }
  await assert.rejects(mockRequest("/profile", { method: "PUT" }), /нет mock-ответа/);
  await assert.rejects(mockRequest("/diary/"), /нет mock-ответа/);
  await assert.rejects(mockRequest("/diary/a/b", { method: "PATCH" }), /нет mock-ответа/);
  await assert.rejects(mockRequest("/health", { scenario: "empty" }), /нет сценария/);
  await assert.rejects(mockRequest("/diary", { scenario: "forbidden" }), /нет сценария/);
  assert.equal(requests.length, 0);
});

test("an unavailable fixture reports a file-loading error", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response("", { status: 404 }));
  await assert.rejects(loadMock("profile"), /Не удалось загрузить mock-файл profile: 404/);
});
