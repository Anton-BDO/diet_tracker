import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { createApiClient, ApiError } from "../../frontend/js/api.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: key => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: key => data.delete(key),
  };
}

// Сквозная проверка: у каждого метода клиента есть mock-ответ
// с актуальной схемой, поэтому демо-режим (?mock=1) работает целиком.
test("mock client supports every API method with current schemas",
  async (context) => {
    context.mock.method(globalThis, "fetch", async (url) => {
      const target = fileURLToPath(url);
      return new Response(await readFile(target), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    const client = createApiClient({ mock: true, storage: memoryStorage() });

  assert.equal((await client.health()).status ?? "ok", "ok");
  assert.ok((await client.register({
    email: "user@example.com", password: "strongpassword123",
    name: "Алексей", sex: "male", birth_date: "1996-03-15",
    height_cm: 180, weight_kg: 80, activity: 1.55, goal: "lose",
  })).token);
  assert.ok((await client.login({
    email: "user@example.com", password: "strongpassword123",
  })).token);

  const products = await client.products("курина");
  assert.ok(Array.isArray(products) && products.length);
  const created = await client.createProduct({
    name: "Свой", kcal: 100, protein: 1, fat: 1, carbs: 1,
  });
  assert.ok(created.id);

  const entry = await client.createEntry({
    product_id: created.id, grams: 100, meal: "lunch", date: "2026-10-20",
  });
  assert.ok(entry.id);
  const updated = await client.updateEntry(entry.id, { grams: 150 });
  assert.ok(updated.id && typeof updated.grams === "number");
  assert.equal(await client.deleteEntry(entry.id), null);

  const day = await client.daySummary("2026-10-20");
  assert.ok(day.totals && day.norm && day.remaining);
  assert.equal(typeof day.is_success, "boolean");

  const streak = await client.streak("2026-10-20");
  assert.equal(typeof streak.current, "number");

  const logged = await client.logWeight({ weight_kg: 80, date: "2026-10-20" });
  assert.equal(typeof logged.weight_kg, "number");
  const history = await client.weightHistory();
  assert.ok(Array.isArray(history));

  const stats = await client.caloriesStats({ days: 7, today: "2026-10-20" });
  assert.equal(stats.days.length, 7);

  const patched = await client.updateProfile({ weight_kg: 79 });
  assert.ok(patched.norm);

  assert.equal(await client.logout(), null);
});

test("real client sends Bearer token from storage", async () => {
  const storage = memoryStorage();
  storage.setItem("token", "token-abc");
  const calls = [];
  const client = createApiClient({
    storage,
    fetchImpl: async (url, options) => {
      calls.push(options.headers);
      return new Response("{}", {
        status: 200, headers: { "Content-Type": "application/json" },
      });
    },
  });

  await client.profile();

  assert.equal(calls[0].Authorization, "Bearer token-abc");
});

test("401 clears token and notifies auth:expired", async () => {
  const storage = memoryStorage();
  storage.setItem("token", "dead-token");
  let expired = 0;
  const client = createApiClient({
    storage,
    onUnauthorized: () => { expired += 1; },
    fetchImpl: async () => new Response(JSON.stringify({
      error: { code: "unauthorized", message: "Требуется действующая Bearer-сессия" },
    }), { status: 401, headers: { "Content-Type": "application/json" } }),
  });

  await assert.rejects(() => client.profile(), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 401);
    assert.equal(error.code, "unauthorized");
    return true;
  });

  assert.equal(storage.getItem("token"), null);
  assert.equal(expired, 1);
});

test("error responses preserve status, code, message and field", async () => {
  const client = createApiClient({
    storage: memoryStorage(),
    fetchImpl: async () => new Response(JSON.stringify({
      error: {
        code: "validation_error",
        message: "Рост должен быть от 100 до 250 см",
        field: "height_cm",
      },
    }), { status: 400, headers: { "Content-Type": "application/json" } }),
  });

  await assert.rejects(
    () => client.updateProfile({ height_cm: 90 }),
    (error) => {
      assert.equal(error.status, 400);
      assert.equal(error.code, "validation_error");
      assert.equal(error.field, "height_cm");
      assert.match(error.message, /рост/i);
      return true;
    },
  );
});
