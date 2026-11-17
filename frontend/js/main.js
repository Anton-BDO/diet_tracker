import { api } from "./api.js";
import { store } from "./store.js";
import { createThemeManager } from "./theme.js";
import { renderLogin } from "./views/login.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderAddFood } from "./views/add-food.js";
import { renderProfile } from "./views/profile.js";
import { renderStats } from "./views/stats.js";

const root = document.getElementById("app");
let cleanup = () => {};

const themeManager = createThemeManager({
  onChange: (theme) => {
    const button = document.getElementById("theme-toggle");
    if (!button) return;
    button.setAttribute(
      "aria-label",
      theme === "dark" ? "Включить светлую тему" : "Включить тёмную тему",
    );
    button.querySelector("[data-theme-icon]").textContent =
      theme === "dark" ? "☀️" : "🌙";
    // Сообщаем экранам (статистика перерисует графики новыми цветами).
    globalThis.dispatchEvent?.(new CustomEvent("themechange", {
      detail: { theme },
    }));
  },
});
document.getElementById("theme-toggle")
  ?.addEventListener("click", () => themeManager.toggle());

function renderRoute() {
  cleanup();
  cleanup = () => {};
  const raw = location.hash.slice(1) || "/dashboard";
  const [path, queryString] = raw.split("?");
  const query = new URLSearchParams(queryString ?? "");
  if (!store.isAuthenticated() && path !== "/login") {
    location.replace("#/login");
    return;
  }
  if (store.isAuthenticated() && path === "/login") {
    location.replace("#/dashboard");
    return;
  }
  if (path === "/login") {
    cleanup = renderLogin(root, {
      store, mock: api.mock,
      onSuccess: () => { location.hash = "/dashboard"; },
    });
    return;
  }
  if (path === "/add-food") {
    cleanup = renderAddFood(root, {
      store,
      entryId: query.get("entry"),
      onDone: () => { location.hash = "/dashboard"; },
    });
    return;
  }
  if (path === "/profile") {
    cleanup = renderProfile(root, { store });
    return;
  }
  if (path === "/stats") {
    cleanup = renderStats(root);
    return;
  }
  if (path !== "/dashboard") {
    location.replace("#/dashboard");
    return;
  }

  cleanup = renderDashboard(root, {
    store,
    onLogout: async () => {
      try {
        await store.logout();
      } catch {
        store.clearSession();
      } finally {
        location.replace("#/login");
      }
    }
  });
}

window.addEventListener("auth:expired", () => {
  store.clearSession();
  if (location.hash !== "#/login") location.replace("#/login");
});

async function start() {
  await store.restore();
  window.addEventListener("hashchange", renderRoute);
  renderRoute();
}

start();
