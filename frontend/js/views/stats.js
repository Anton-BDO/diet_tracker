import { api } from "../api.js";
import { localDate } from "../auth-validation.js";
import { drawCaloriesChart, drawWeightChart } from "../charts.js";
import { renderNav } from "./nav.js";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function caloriesTable(days) {
  const table = el("table", "data-table");
  const head = el("tr");
  head.appendChild(el("th", "", "Дата"));
  head.appendChild(el("th", "", "Ккал"));
  head.appendChild(el("th", "", "День"));
  table.appendChild(head);
  for (const day of days) {
    const tr = el("tr");
    tr.appendChild(el("td", "", day.date));
    tr.appendChild(el("td", "", String(day.kcal)));
    tr.appendChild(el("td", "", day.is_success
      ? "В пределах нормы" : "Вне нормы"));
    table.appendChild(tr);
  }
  return table;
}

function weightTable(points) {
  const table = el("table", "data-table");
  const head = el("tr");
  head.appendChild(el("th", "", "Дата"));
  head.appendChild(el("th", "", "Вес, кг"));
  table.appendChild(head);
  for (const point of points) {
    const tr = el("tr");
    tr.appendChild(el("td", "", point.date));
    tr.appendChild(el("td", "", String(point.weight_kg)));
    table.appendChild(tr);
  }
  return table;
}

export function renderStats(root) {
  const screen = el("section", "dashboard-container");
  screen.setAttribute("aria-labelledby", "stats-title");
  screen.appendChild(el("h1", "screen-title", "Статистика"));
  let caloriesTableOpen = false;
  let weightTableOpen = false;

  const caloriesBox = el("div", "chart-box");
  caloriesBox.appendChild(el("h2", "dashboard-meals-title",
    "Калории за 7 дней (пунктир — норма)"));
  screen.appendChild(caloriesBox);
  const caloriesTableBox = el("div");
  screen.appendChild(caloriesTableBox);
  const grid = el("div", "stats-grid");
  screen.insertBefore(grid, caloriesTableBox);

  const weightBox = el("div", "chart-box");
  weightBox.appendChild(el("h2", "dashboard-meals-title", "Динамика веса"));
  screen.appendChild(weightBox);
  const weightTableBox = el("div");
  grid.append(caloriesBox, weightBox);
  screen.appendChild(weightTableBox);
  screen.appendChild(renderNav("stats"));
  root.replaceChildren(screen);

  let redrawCalories = () => {};
  let redrawWeight = () => {};
  const onResize = () => { redrawCalories(); redrawWeight(); };
  const onThemeChange = () => { redrawCalories(); redrawWeight(); };
  globalThis.addEventListener("resize", onResize);
  globalThis.addEventListener("themechange", onThemeChange);

  async function loadStats() {
    for (const node of [...caloriesBox.children]) {
      if (node.tagName !== "H2") node.remove();
    }
    caloriesBox.appendChild(el("p", "muted", "Загрузка…"));
    try {
      const stats = await api.caloriesStats({
        days: 7, today: localDate(),
      });
      caloriesBox.querySelector(".muted")?.remove();
      caloriesBox.appendChild(el("p", "muted",
        `Норма: ${stats.norm_kcal} ккал`));
      const canvas = el("canvas");
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", "Столбчатый график калорий по дням");
      caloriesBox.appendChild(canvas);
      redrawCalories = () => drawCaloriesChart(canvas, {
        days: stats.days, normKcal: stats.norm_kcal,
      });
      requestAnimationFrame(redrawCalories);
      caloriesTableBox.replaceChildren();
      const caloriesToggle = el("button", "button-secondary table-toggle",
        caloriesTableOpen ? "Скрыть данные по дням" : "Показать данные по дням");
      caloriesToggle.setAttribute("aria-expanded", String(caloriesTableOpen));
      caloriesToggle.addEventListener("click", () => {
        caloriesTableOpen = !caloriesTableOpen;
        loadStats();
      });
      caloriesTableBox.appendChild(caloriesToggle);
      if (caloriesTableOpen) caloriesTableBox.appendChild(caloriesTable(stats.days));
      if (!stats.days.some(day => day.kcal > 0)) {
        caloriesBox.appendChild(el(
          "p", "muted", "За этот период пока нет записей",
        ));
      }
    } catch (error) {
      caloriesBox.querySelector(".muted")?.remove();
      caloriesBox.appendChild(el(
        "p", "form-error", error.message || "Не удалось загрузить статистику",
      ));
    }
  }

  async function loadWeight() {
    for (const node of [...weightBox.children]) {
      if (node.tagName !== "H2") node.remove();
    }
    try {
      const points = await api.weightHistory();
      redrawWeight = () => {};
      if (!points.length) {
        weightBox.appendChild(el("p", "muted", "Замеров веса пока нет"));
        return;
      }
      const canvas = el("canvas");
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", "Линейный график веса");
      weightBox.appendChild(canvas);
      redrawWeight = () => drawWeightChart(canvas, points);
      requestAnimationFrame(redrawWeight);
      weightTableBox.replaceChildren();
      const weightToggle = el("button", "button-secondary table-toggle",
        weightTableOpen ? "Скрыть историю" : "Показать всю историю");
      weightToggle.setAttribute("aria-expanded", String(weightTableOpen));
      weightToggle.addEventListener("click", () => {
        weightTableOpen = !weightTableOpen;
        loadWeight();
      });
      weightTableBox.appendChild(weightToggle);
      if (weightTableOpen) weightTableBox.appendChild(weightTable(points));
    } catch (error) {
      weightBox.appendChild(el(
        "p", "form-error", error.message || "Не удалось загрузить вес",
      ));
    }
  }

  loadStats();
  loadWeight();

  return () => {
    globalThis.removeEventListener("resize", onResize);
    globalThis.removeEventListener("themechange", onThemeChange);
  };
}
