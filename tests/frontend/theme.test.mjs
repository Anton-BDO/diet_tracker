import assert from "node:assert/strict";
import test from "node:test";
import {
  THEME_KEY,
  createThemeManager,
  nextTheme,
  resolveInitialTheme,
} from "../../frontend/js/theme.js";

test("resolveInitialTheme uses saved value when valid", () => {
  assert.equal(resolveInitialTheme("light", true), "light");
  assert.equal(resolveInitialTheme("dark", false), "dark");
});

test("resolveInitialTheme falls back to system preference", () => {
  assert.equal(resolveInitialTheme(null, true), "dark");
  assert.equal(resolveInitialTheme(null, false), "light");
  assert.equal(resolveInitialTheme(undefined, undefined), "light");
});

test("resolveInitialTheme ignores invalid saved values", () => {
  assert.equal(resolveInitialTheme("blue", true), "dark");
  assert.equal(resolveInitialTheme("", false), "light");
});

test("nextTheme alternates themes", () => {
  assert.equal(nextTheme("dark"), "light");
  assert.equal(nextTheme("light"), "dark");
});

function memoryStorage(initial = null, { broken = false } = {}) {
  let value = initial;
  return {
    getItem: () => {
      if (broken) throw new Error("denied");
      return value;
    },
    setItem: (_key, next) => {
      if (broken) throw new Error("denied");
      value = next;
    },
  };
}

function fakeRoot() {
  return { dataset: {}, style: {} };
}

function fakeMedia(matches) {
  return {
    matches,
    addEventListener: () => {},
  };
}

test("manager applies system dark theme without saved value", () => {
  const root = fakeRoot();
  const manager = createThemeManager({
    storage: memoryStorage(),
    matchMediaImpl: () => fakeMedia(true),
    root,
  });
  assert.equal(manager.getTheme(), "dark");
  assert.equal(root.dataset.theme, "dark");
});

test("toggle persists choice and notifies listener", () => {
  const storage = memoryStorage();
  const seen = [];
  const manager = createThemeManager({
    storage,
    matchMediaImpl: () => fakeMedia(false),
    root: fakeRoot(),
    onChange: theme => seen.push(theme),
  });
  manager.toggle();
  assert.equal(manager.getTheme(), "dark");
  assert.equal(storage.getItem(THEME_KEY), "dark");
  assert.deepEqual(seen, ["light", "dark"]);
});

test("broken storage does not crash and keeps session theme", () => {
  const root = fakeRoot();
  const manager = createThemeManager({
    storage: memoryStorage(null, { broken: true }),
    matchMediaImpl: () => fakeMedia(true),
    root,
  });
  assert.doesNotThrow(() => manager.toggle());
  assert.equal(root.dataset.theme, "light");
});

test("manager works without matchMedia", () => {
  const manager = createThemeManager({
    storage: memoryStorage(),
    matchMediaImpl: undefined,
    root: fakeRoot(),
  });
  assert.equal(manager.getTheme(), "light");
});

test("saved theme wins over system preference", () => {
  const manager = createThemeManager({
    storage: memoryStorage("dark"),
    matchMediaImpl: () => fakeMedia(false),
    root: fakeRoot(),
  });
  assert.equal(manager.getTheme(), "dark");
});

test("storage key matches the spec", () => {
  assert.equal(THEME_KEY, "diet_tracker_theme");
});
