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

  const caloriesBox = el("div", "chart-box");
  caloriesBox.appendChild(el("h2", "dashboard-meals-title",
    "Калории за 7 дней (пунктир — норма)"));
  screen.appendChild(caloriesBox);
  const caloriesTableBox = el("div");
  screen.appendChild(caloriesTableBox);

  const weightBox = el("div", "chart-box");
  weightBox.appendChild(el("h2", "dashboard-meals-title", "Динамика веса"));
  screen.appendChild(weightBox);
  const weightTableBox = el("div");
  screen.appendChild(weightTableBox);
  screen.appendChild(renderNav("stats"));
  root.replaceChildren(screen);

  const redraws = [];
  const onResize = () => redraws.forEach(redraw => redraw());
  globalThis.addEventListener("resize", onResize);

  async function loadStats() {
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
      const redraw = () => drawCaloriesChart(canvas, {
        days: stats.days, normKcal: stats.norm_kcal,
      });
      redraws.push(redraw);
      requestAnimationFrame(redraw);
      caloriesTableBox.replaceChildren(caloriesTable(stats.days));
    } catch (error) {
      caloriesBox.querySelector(".muted")?.remove();
      caloriesBox.appendChild(el(
        "p", "form-error", error.message || "Не удалось загрузить статистику",
      ));
    }
  }

  async function loadWeight() {
    try {
      const points = await api.weightHistory();
      if (!points.length) {
        weightBox.appendChild(el("p", "muted", "Замеров веса пока нет"));
        return;
      }
      const canvas = el("canvas");
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", "Линейный график веса");
      weightBox.appendChild(canvas);
      const redraw = () => drawWeightChart(canvas, points);
      redraws.push(redraw);
      requestAnimationFrame(redraw);
      weightTableBox.replaceChildren(weightTable(points));
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
  };
}
