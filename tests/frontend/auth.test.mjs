import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { ageOn, localDate, validateAuth } from "../../frontend/js/auth-validation.js";
import { ApiError, createApiClient } from "../../frontend/js/api.js";
import { createAuthStore } from "../../frontend/js/store.js";

const today = new Date(2026, 9, 20, 12);
const profile = {
  id: "demo-user", name: "Тестовый пользователь",
  norm: { kcal: 2437, protein: 183, fat: 81, carbs: 244 },
};
const registration = {
  email: "demo@example.com", password: "demo-password", name: "Демо",
  sex: "male", birth_date: "2001-01-15", height_cm: "180", weight_kg: "84.5",
  activity: "1.55", goal: "lose",
};

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: key => data.delete(key),
  };
}

test("login trims email but preserves password", () => {
  const result = validateAuth("login", { email: " demo@example.com ", password: " pass " });
  assert.deepEqual(result.errors, {});
  assert.deepEqual(result.data, { email: "demo@example.com", password: " pass " });
  assert.deepEqual(Object.keys(validateAuth("login", {}).errors), ["email", "password"]);
});

test("registration produces the architecture payload with numeric values", () => {
  const result = validateAuth("register", registration, today);
  assert.deepEqual(result.errors, {});
  assert.equal(result.data.height_cm, 180);
  assert.equal(result.data.weight_kg, 84.5);
  assert.equal(result.data.activity, 1.55);
  assert.equal(result.data.sex, "male");
  assert.equal(result.data.birth_date, "2001-01-15");
  assert.equal(result.data.goal, "lose");
  assert.deepEqual(Object.keys(validateAuth("register", {}, today).errors).sort(), [
    "activity", "birth_date", "email", "goal", "height_cm", "name", "password", "sex", "weight_kg",
  ]);
});

test("height and weight boundaries are inclusive and finite", () => {
  for (const [field, valid, invalid] of [
    ["height_cm", [100, 250], [99.9, 250.1, "", "NaN", "Infinity"]],
    ["weight_kg", [30, 300], [29.9, 300.1, "", "NaN", "Infinity"]],
  ]) {
    for (const value of valid) {
      assert.equal(validateAuth("register", { ...registration, [field]: value }, today).errors[field], undefined);
    }
    for (const value of invalid) {
      assert.ok(validateAuth("register", { ...registration, [field]: value }, today).errors[field]);
    }
  }
});

test("age is calculated on the birthday and invalid calendar dates are rejected", () => {
  assert.equal(ageOn("2012-10-20", today), 14);
  assert.equal(ageOn("2012-10-21", today), 13);
  assert.equal(ageOn("1925-10-21", today), 100);
  assert.equal(ageOn("1925-10-20", today), 101);
  for (const value of ["2012-10-21", "1925-10-20", "2001-02-29", "2027-01-01", "bad"]) {
    assert.ok(validateAuth("register", { ...registration, birth_date: value }, today).errors.birth_date);
  }
  for (const value of ["2012-10-20", "1925-10-21", "2000-02-29"]) {
    assert.equal(validateAuth("register", { ...registration, birth_date: value }, today).errors.birth_date, undefined);
  }
  assert.equal(localDate(today), "2026-10-20");
});

test("all five activities and three goals are supported", () => {
  for (const activity of [1.2, 1.375, 1.55, 1.725, 1.9]) {
    assert.equal(validateAuth("register", { ...registration, activity }, today).errors.activity, undefined);
  }
  for (const goal of ["lose", "keep", "gain"]) {
    assert.equal(validateAuth("register", { ...registration, goal }, today).errors.goal, undefined);
  }
  const result = validateAuth("register", {
    ...registration, activity: "moderate", goal: "maintain", sex: "unknown", password: "short",
  }, today);
  assert.deepEqual(Object.keys(result.errors).sort(), ["activity", "goal", "password", "sex"]);
});

test("real API uses Bearer auth and sends the expected JSON", async () => {
  const storage = memoryStorage({ token: "real-session", mock_token: "demo-session" });
  const calls = [];
  const client = createApiClient({ storage, fetchImpl: async (url, options) => {
    calls.push({ url, ...options });
    return new Response(JSON.stringify({ token: "new-session" }));
  } });
  await client.login({ email: "demo@example.com", password: "password" });
  await client.profile();
  assert.equal(calls[0].url, "/api/auth/login");
  assert.equal(calls[0].method, "POST");
  assert.equal(calls[0].headers.Authorization, "Bearer real-session");
  assert.deepEqual(JSON.parse(calls[0].body), {
    email: "demo@example.com", password: "password",
  });
  assert.equal(calls[1].url, "/api/profile");
  assert.equal(calls[1].body, undefined);
});

test("logout does not attempt to parse a 204 body", async () => {
  const client = createApiClient({ fetchImpl: async () => ({
    status: 204, ok: true, json: () => assert.fail("204 has no JSON body"),
  }) });
  assert.equal(await client.logout(), null);
});

test("server validation preserves the target field", async () => {
  const client = createApiClient({ fetchImpl: async () => new Response(JSON.stringify({
    error: { code: "validation_error", message: "Неверный рост", field: "height_cm" },
  }), { status: 400 }) });
  await assert.rejects(client.register(registration), error => error instanceof ApiError
    && error.status === 400 && error.field === "height_cm" && error.message === "Неверный рост");
});

test("401 removes only the active token and reports expired auth", async () => {
  const storage = memoryStorage({ token: "expired", mock_token: "keep-demo" });
  let expired = 0;
  const client = createApiClient({ storage,
    onUnauthorized: () => { expired += 1; },
    fetchImpl: async () => new Response(JSON.stringify({ error: { code: "unauthorized" } }), { status: 401 }),
  });
  await assert.rejects(client.profile(), { status: 401 });
  assert.equal(storage.getItem("token"), null);
  assert.equal(storage.getItem("mock_token"), "keep-demo");
  assert.equal(expired, 1);
});

test("a real request never sends a demo token", async () => {
  const client = createApiClient({ storage: memoryStorage({ mock_token: "demo" }),
    fetchImpl: async (url, options) => {
      assert.equal(options.headers.Authorization, undefined);
      return new Response(JSON.stringify(profile));
    },
  });
  await client.profile();
});

test("invalid JSON gives a readable error and still expires a 401 session", async () => {
  const storage = memoryStorage({ token: "expired" });
  let expired = false;
  const client = createApiClient({ storage,
    onUnauthorized: () => { expired = true; },
    fetchImpl: async () => new Response("not JSON", { status: 401 }),
  });
  await assert.rejects(client.profile(), {
    code: "invalid_response", status: 401,
    message: "Сервер вернул некорректный ответ. Попробуйте позже",
  });
  assert.equal(storage.getItem("token"), null);
  assert.equal(expired, true);
});

test("mock auth loads fixtures and uses a separate token namespace", async (context) => {
  context.mock.method(globalThis, "fetch", async url => new Response(await readFile(url)));
  const client = createApiClient({ mock: true, fetchImpl: () => assert.fail("No real API") });
  assert.equal(client.tokenKey, "mock_token");
  assert.ok((await client.login(registration)).token);
  assert.equal((await client.register(registration)).profile.norm.kcal, 2437);
  const errorClient = createApiClient({ mock: true, mockScenario: "registration-validation" });
  assert.equal((await errorClient.health()).status, "ok");
  await assert.rejects(errorClient.register(registration), { status: 400, field: "height_cm" });
});

test("login stores the token before requesting the profile", async () => {
  const storage = memoryStorage();
  const client = {
    login: async () => ({ token: "session" }),
    profile: async () => {
      assert.equal(storage.getItem("token"), "session");
      return profile;
    },
  };
  const store = createAuthStore({ client, storage });
  const updates = [];
  const unsubscribe = store.subscribe(state => updates.push(state));
  assert.deepEqual(await store.login(registration), profile);
  assert.ok(updates.some(state => state.pending));
  assert.equal(store.getState().pending, false);
  assert.equal(store.isAuthenticated(), true);
  unsubscribe();
  const count = updates.length;
  store.clearSession();
  assert.equal(updates.length, count);
  assert.equal(store.isAuthenticated(), false);
});

test("registration uses the returned profile without another request", async () => {
  const storage = memoryStorage();
  const store = createAuthStore({ storage, client: {
    register: async () => ({ token: "session", profile }),
    profile: () => assert.fail("Profile is already returned"),
  } });
  assert.deepEqual(await store.register(registration), profile);
  assert.equal(storage.getItem("token"), "session");
});

test("a failed login or missing token never leaves an authenticated state", async () => {
  for (const result of [{}, { token: "session" }]) {
    const storage = memoryStorage();
    const store = createAuthStore({ storage, client: {
      login: async () => result,
      profile: async () => { throw new Error("Profile failed"); },
    } });
    const states = [];
    store.subscribe(state => states.push(state));
    await assert.rejects(store.login(registration));
    assert.equal(storage.getItem("token"), null);
    assert.equal(store.getState().profile, null);
    assert.equal(store.getState().pending, false);
    assert.ok(store.getState().error);
    assert.ok(states.filter(state => state.error).every(state => !state.pending));
  }
});

test("restore handles saved, expired and temporarily unavailable sessions", async () => {
  const storage = memoryStorage({ token: "saved" });
  const valid = createAuthStore({ storage, client: { profile: async () => profile } });
  assert.deepEqual(await valid.restore(), profile);
  assert.equal(valid.isAuthenticated(), true);
  for (const status of [500, 401]) {
    const broken = createAuthStore({ storage, client: { profile: async () => {
      throw new ApiError(status, "error", "Ошибка запроса");
    } } });
    assert.equal(await broken.restore(), null);
    assert.equal(broken.isAuthenticated(), false);
    assert.equal(Boolean(storage.getItem("token")), status !== 401);
  }
  const empty = createAuthStore({ storage, client: { profile: () => assert.fail("No token") } });
  assert.equal(await empty.restore(), null);
});

test("logout clears local auth even when the server is unavailable", async () => {
  const storage = memoryStorage({ token: "saved" });
  const store = createAuthStore({ storage, client: {
    profile: async () => profile,
    logout: async () => { throw new Error("Offline"); },
  } });
  await store.restore();
  await assert.rejects(store.logout(), /Offline/);
  assert.equal(storage.getItem("token"), null);
  assert.equal(store.getState().profile, null);
});

test("a second auth request is rejected while the first is pending", async () => {
  let finish;
  const pending = new Promise(resolve => { finish = resolve; });
  const store = createAuthStore({ storage: memoryStorage(), client: {
    login: async () => { await pending; return { token: "session", profile }; },
  } });
  const first = store.login(registration);
  assert.equal(store.getState().pending, true);
  await assert.rejects(store.login(registration), /Дождитесь/);
  finish();
  await first;
  assert.equal(store.isAuthenticated(), true);
});
