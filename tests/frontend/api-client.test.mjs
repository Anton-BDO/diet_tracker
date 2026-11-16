import assert from "node:assert/strict";
import test from "node:test";
import { createApiClient } from "../../frontend/js/api.js";
import { createAuthStore } from "../../frontend/js/store.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: key => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: key => data.delete(key),
  };
}

function clientWith(calls, handler) {
  return createApiClient({
    storage: memoryStorage(),
    fetchImpl: async (url, options) => {
      calls.push({ url, ...options });
      return handler(url, options);
    },
  });
}

const okJson = payload => new Response(JSON.stringify(payload), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

test("streak hits /api/streak with encoded today", async () => {
  const calls = [];
  const client = clientWith(calls, () => okJson({ current: 3, record: 5 }));

  const result = await client.streak("2026-10-20");

  assert.deepEqual(result, { current: 3, record: 5 });
  assert.equal(calls[0].url, "/api/streak?today=2026-10-20");
  assert.equal(calls[0].method, "GET");
});

test("streak without today has no query string", async () => {
  const calls = [];
  const client = clientWith(calls, () => okJson({ current: 0, record: 0 }));

  await client.streak();

  assert.equal(calls[0].url, "/api/streak");
});

test("products encodes query with URLSearchParams", async () => {
  const calls = [];
  const client = clientWith(calls, () => okJson([]));

  await client.products("куриная грудка");

  assert.equal(
    calls[0].url,
    `/api/products?${new URLSearchParams({ q: "куриная грудка" })}`,
  );
});

test("entry methods use correct paths and methods", async () => {
  const calls = [];
  const client = clientWith(calls, () => okJson({ id: "42" }));

  await client.createEntry({ product_id: "1", grams: 100 });
  await client.updateEntry("42", { grams: 150 });
  await client.deleteEntry("42");

  assert.equal(calls[0].url, "/api/diary");
  assert.equal(calls[0].method, "POST");
  assert.equal(calls[1].url, "/api/diary/42");
  assert.equal(calls[1].method, "PATCH");
  assert.equal(calls[2].url, "/api/diary/42");
  assert.equal(calls[2].method, "DELETE");
});

test("deleteEntry resolves to null on 204", async () => {
  const client = clientWith([], () => new Response(null, { status: 204 }));
  assert.equal(await client.deleteEntry("42"), null);
});

test("weightHistory and caloriesStats build queries", async () => {
  const calls = [];
  const client = clientWith(calls, () => okJson([]));

  await client.weightHistory({ from: "2026-10-01", to: "2026-10-31" });
  await client.weightHistory();
  await client.caloriesStats({ days: 14, today: "2026-10-20" });
  await client.logWeight({ weight_kg: 80, date: "2026-10-20" });

  assert.equal(calls[0].url, "/api/weight?from=2026-10-01&to=2026-10-31");
  assert.equal(calls[1].url, "/api/weight");
  assert.equal(calls[2].url, "/api/stats/calories?days=14&today=2026-10-20");
  assert.equal(calls[3].method, "POST");
});

test("store loads day summary and streak together", async () => {
  const day = {
    date: "2026-10-20",
    entries: [],
    totals: { kcal: 0, protein: 0, fat: 0, carbs: 0 },
    norm: { kcal: 2345, protein: 176, fat: 78, carbs: 235 },
    remaining: { kcal: 2345, protein: 176, fat: 78, carbs: 235 },
    is_success: false,
  };
  const client = {
    tokenKey: "token",
    daySummary: async () => day,
    streak: async () => ({ current: 2, record: 4 }),
  };
  const store = createAuthStore({ client, storage: memoryStorage() });

  await store.loadDashboard();

  assert.deepEqual(store.getState().daySummary, day);
  assert.deepEqual(store.getState().streak, { current: 2, record: 4 });
  assert.equal(store.getState().error, null);
});

test("store deleteEntry refreshes dashboard data", async () => {
  let streakCalls = 0;
  const client = {
    tokenKey: "token",
    daySummary: async () => ({
      date: "2026-10-20",
      entries: [],
      totals: { kcal: 0, protein: 0, fat: 0, carbs: 0 },
      norm: { kcal: 2345, protein: 176, fat: 78, carbs: 235 },
      remaining: { kcal: 2345, protein: 176, fat: 78, carbs: 235 },
      is_success: false,
    }),
    streak: async () => ({ current: (streakCalls += 1), record: 1 }),
    deleteEntry: async () => {},
  };
  const store = createAuthStore({ client, storage: memoryStorage() });
  await store.loadDashboard();
  assert.equal(store.getState().streak.current, 1);

  await store.deleteEntry("42");

  assert.equal(store.getState().streak.current, 2);
});
