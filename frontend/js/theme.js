// Управление светлой/тёмной темой интерфейса.

export const THEME_KEY = "diet_tracker_theme";
export const THEMES = ["light", "dark"];

const THEME_COLORS = { light: "#f5f7fa", dark: "#0f1419" };

// Чистые функции — тестируются во встроенном раннере Node без DOM.
export function resolveInitialTheme(saved, prefersDark) {
  if (THEMES.includes(saved)) return saved;
  return prefersDark ? "dark" : "light";
}

export function nextTheme(theme) {
  return theme === "dark" ? "light" : "dark";
}

export function createThemeManager({
  storage = globalThis.localStorage,
  matchMediaImpl = globalThis.matchMedia?.bind(globalThis),
  root = globalThis.document?.documentElement,
  onChange = () => {},
} = {}) {
  let media = null;
  try {
    media = matchMediaImpl?.("(prefers-color-scheme: dark)") ?? null;
  } catch {
    media = null;
  }

  let saved = null;
  try {
    saved = storage?.getItem(THEME_KEY) ?? null;
  } catch {
    saved = null; // хранилище недоступно — тема живёт только в сессии
  }

  let theme = resolveInitialTheme(saved, Boolean(media?.matches));
  let manual = THEMES.includes(saved);

  function apply() {
    if (root) {
      root.dataset.theme = theme;
      root.style.colorScheme = theme;
    }
    const meta = globalThis.document?.querySelector(
      'meta[name="theme-color"]',
    );
    if (meta) meta.content = THEME_COLORS[theme];
    onChange(theme);
  }

  function toggle() {
    theme = nextTheme(theme);
    manual = true;
    try {
      storage?.setItem(THEME_KEY, theme);
    } catch {
      // запомнить не удалось: переключаем только на текущую сессию
    }
    apply();
  }

  media?.addEventListener?.("change", (event) => {
    if (!manual) {
      theme = event.matches ? "dark" : "light";
      apply();
    }
  });

  apply();

  return {
    getTheme: () => theme,
    toggle,
    apply,
  };
}
