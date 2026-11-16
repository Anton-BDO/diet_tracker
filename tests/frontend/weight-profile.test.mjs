import assert from "node:assert/strict";
import test from "node:test";
import { createAuthStore } from "../../frontend/js/store.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: key => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: key => data.delete(key),
  };
}

function profileOf(weightKg) {
  return {
    id: "user-1",
    email: "user@example.com",
    name: "Алексей",
    sex: "male",
    birth_date: "1996-03-15",
    height_cm: 180,
    weight_kg: weightKg,
    activity: 1.55,
    goal: "lose",
    norm: weightKg > 70
      ? { kcal: 2345, protein: 176, fat: 78, carbs: 235 }
      : { kcal: 2280, protein: 171, fat: 76, carbs: 228 },
  };
}

test("store.restore picks up new weight and norm after logWeight", async () => {
  const storage = memoryStorage();
  storage.setItem("token", "token-abc");
  let current = profileOf(80);
  const client = {
    tokenKey: "token",
    logWeight: async (body) => {
      current = profileOf(body.weight_kg);
      return { id: "w1", date: body.date, weight_kg: body.weight_kg };
    },
    profile: async () => current,
  };
  const store = createAuthStore({ client, storage });

  await store.restore();
  assert.equal(store.getState().profile.weight_kg, 80);

  await client.logWeight({ weight_kg: 70, date: "2026-10-20" });
  await store.restore();

  assert.equal(store.getState().profile.weight_kg, 70);
  assert.equal(store.getState().profile.norm.kcal, 2280);
});
