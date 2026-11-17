import { api } from "../api.js";
import { localDate } from "../auth-validation.js";
import { renderNav } from "./nav.js";

const MEALS = [
  ["breakfast", "Завтрак"],
  ["lunch", "Обед"],
  ["dinner", "Ужин"],
  ["snack", "Перекус"],
];

const GRAMS_MIN = 1;
const GRAMS_MAX = 5000;
const SEARCH_DELAY_MS = 300;
const NUTRIENT_KEYS = ["kcal", "protein", "fat", "carbs"];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function round1(value) {
  return Math.round(value * 10) / 10;
}

// Чистые помощники вынесены отдельно, чтобы их можно было тестировать
// во встроенном раннере Node без DOM.

export function resolveEditing(entryId, daySummary) {
  // Решить, что делать с параметром entryId: создать, ждать или править.
  if (!entryId) return { status: "create" };
  if (!daySummary) return { status: "loading" };
  const entry = (daySummary.entries ?? []).find(item => item.id === entryId);
  if (!entry) return { status: "missing" };
  return { status: "edit", entry };
}

export function previewOf(product, grams) {
  // КБЖУ порции или null, если данных недостаточно для расчёта.
  if (!product || !NUTRIENT_KEYS.every(
    key => Number.isFinite(Number(product[key])),
  )) {
    return null;
  }
  if (!Number.isFinite(grams) || grams < GRAMS_MIN) return null;
  const factor = Math.min(grams, GRAMS_MAX) / 100;
  return {
    kcal: round1(product.kcal * factor),
    protein: round1(product.protein * factor),
    fat: round1(product.fat * factor),
    carbs: round1(product.carbs * factor),
  };
}

export function renderAddFood(root, { store, entryId = null, onDone }) {
  const resolution = resolveEditing(entryId, store.getState().daySummary);
  if (resolution.status === "loading") {
    root.replaceChildren(el("p", "loading-message", "Загрузка…"));
    store.loadDashboard().catch(() => {});
    const unsubscribe = store.subscribe(state => {
      if (state.daySummary || state.error) {
        unsubscribe();
        renderAddFood(root, { store, entryId, onDone });
      }
    });
    return unsubscribe;
  }
  if (resolution.status === "missing") {
    const box = el("div", "error-state");
    box.appendChild(el(
      "p", "form-error", "Запись не найдена или недоступна",
    ));
    const back = el("button", "button-secondary", "На главную");
    back.addEventListener("click", () => { location.hash = "/dashboard"; });
    box.appendChild(back);
    root.replaceChildren(box);
    return () => {};
  }

  const editing = resolution.status === "edit" ? resolution.entry : null;
  let timer = null;
  let requestId = 0;

  const screen = el("section", "dashboard-container");
  screen.setAttribute("aria-labelledby", "add-food-title");
  screen.appendChild(el(
    "h1", "screen-title", editing ? "Изменить запись" : "Добавить еду",
  ));

  const form = el("form");
  form.noValidate = true;
  form.className = "stacked-form";
  const errorBox = el("p", "alert alert-error");
  errorBox.setAttribute("role", "alert");
  errorBox.hidden = true;
  form.appendChild(errorBox);

  // При редактировании нет КБЖУ продукта на 100 г (в записи только
  // снимок порции), поэтому выбранный продукт без preview.
  let selected = null;

  if (editing) {
    selected = { id: editing.product_id, name: editing.product_name };
    form.appendChild(el(
      "p", "muted",
      `Продукт: ${editing.product_name} (${editing.kcal} ккал)`,
    ));
  } else {
    const searchLabel = el("label", "", "Продукт или блюдо");
    searchLabel.htmlFor = "product-search";
    const search = el("input");
    search.id = "product-search";
    search.type = "search";
    search.placeholder = "Например, куриная грудка или гречка";
    const results = el("ul", "product-results");
    results.setAttribute("role", "listbox");
    results.setAttribute("aria-label", "Найденные продукты");
    const searchHint = el(
      "p", "muted", "Начните вводить название продукта или блюда",
    );
    const selectedCard = el("div", "selected-product");
    selectedCard.hidden = true;
    form.append(searchLabel, search, searchHint, results, selectedCard);

    let resultsCollapsed = false;

    function showSelected(product) {
      selectedCard.replaceChildren();
      if (!product) {
        selectedCard.hidden = true;
        return;
      }
      selectedCard.hidden = false;
      resultsCollapsed = true;
      results.hidden = true;
      const badge = el("span", "selected-badge", "Выбрано");
      const name = el("strong", "", product.name);
      const nutrients = el(
        "span", "muted",
        `${product.kcal} ккал · Б ${product.protein} г · Ж ${product.fat} г · У ${product.carbs} г на 100 г`,
      );
      const change = el("button", "button-secondary", "Изменить продукт");
      change.addEventListener("click", () => {
        selected = null;
        selectedCard.hidden = true;
        results.hidden = false;
        resultsCollapsed = false;
        search.focus();
        updatePreview();
      });
      selectedCard.append(badge, name, nutrients, change);
    }

    const renderResults = (products) => {
      results.replaceChildren();
      searchHint.hidden = true;
      if (!products.length) {
        results.appendChild(el(
          "li", "muted", "Ничего не найдено. Можно добавить свой продукт",
        ));
        return;
      }
      for (const product of products) {
        const item = el("li");
        const button = el("button");
        button.type = "button";
        const name = el("span", "", `${product.name} `);
        name.appendChild(el(
          "span", "product-kcal",
          `${product.kcal} ккал · Б ${product.protein} · Ж ${product.fat} · У ${product.carbs} (на 100 г)`,
        ));
        button.appendChild(name);
        button.addEventListener("click", () => {
          selected = product;
          showSelected(product);
          updatePreview();
        });
        item.appendChild(button);
        results.appendChild(item);
      }
    };

    const runSearch = async (query) => {
      const id = ++requestId;
      if (!query.trim()) {
        results.replaceChildren();
        searchHint.hidden = false;
        return;
      }
      searchHint.hidden = true;
      results.hidden = false;
      resultsCollapsed = false;
      results.replaceChildren();
      results.appendChild(el("li", "muted", "Ищем продукты…"));
      try {
        const products = await api.products(query.trim());
        // Старый ответ не должен перезаписывать более новый запрос.
        if (id === requestId) renderResults(products);
      } catch (error) {
        if (id === requestId) {
          results.replaceChildren();
          results.appendChild(el("li", "muted",
            error.message || "Не удалось выполнить поиск"));
        }
      }
    };
    search.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => runSearch(search.value), SEARCH_DELAY_MS);
    });

    const customToggle = el("button", "button-secondary",
      "Добавить свой продукт");
    const customForm = el("div");
    customForm.hidden = true;
    customForm.id = "custom-product-form";
    customToggle.setAttribute("aria-expanded", "false");
    customToggle.setAttribute("aria-controls", customForm.id);
    customToggle.addEventListener("click", () => {
      customForm.hidden = !customForm.hidden;
      customToggle.setAttribute(
        "aria-expanded", String(!customForm.hidden));
      customToggle.textContent = customForm.hidden
        ? "Добавить свой продукт" : "Скрыть форму продукта";
    });
    const customFields = {};
    for (const [name, label, step] of [
      ["name", "Название", null],
      ["kcal", "Ккал на 100 г", "0.1"],
      ["protein", "Белки, г", "0.1"],
      ["fat", "Жиры, г", "0.1"],
      ["carbs", "Углеводы, г", "0.1"],
    ]) {
      const fieldLabel = el("label", "", label);
      const input = el("input");
      input.id = `custom-${name}`;
      fieldLabel.htmlFor = input.id;
      input.name = name;
      input.type = step ? "number" : "text";
      if (step) {
        input.min = "0";
        input.step = step;
      }
      customFields[name] = input;
      customForm.append(fieldLabel, input);
    }
    const customSubmit = el("button", "button-primary", "Сохранить продукт");
    customForm.appendChild(customSubmit);
    customSubmit.addEventListener("click", async (event) => {
      event.preventDefault();
      errorBox.hidden = true;
      customSubmit.disabled = true;
      try {
        const raw = {
          name: customFields.name.value.trim(),
          kcal: customFields.kcal.value.trim(),
          protein: customFields.protein.value.trim(),
          fat: customFields.fat.value.trim(),
          carbs: customFields.carbs.value.trim(),
        };
        const emptyField = Object.keys(raw).find(key => !raw[key]);
        if (emptyField) {
          throw new Error("Заполните все поля продукта");
        }
        const body = {
          name: raw.name,
          kcal: Number(raw.kcal),
          protein: Number(raw.protein),
          fat: Number(raw.fat),
          carbs: Number(raw.carbs),
        };
        selected = await api.createProduct(body);
        customForm.hidden = true;
        customToggle.setAttribute("aria-expanded", "false");
        customToggle.textContent = "Добавить свой продукт";
        search.value = selected.name;
        showSelected(selected);
        updatePreview();
      } catch (error) {
        errorBox.textContent = error.message || "Не удалось сохранить продукт";
        errorBox.hidden = false;
      } finally {
        customSubmit.disabled = false;
      }
    });
    form.append(customToggle, customForm);
  }

  const gramsLabel = el("label", "", "Количество, г");
  const grams = el("input");
  grams.type = "number";
  grams.min = String(GRAMS_MIN);
  grams.max = String(GRAMS_MAX);
  grams.step = "1";
  grams.value = editing ? editing.grams : 100;
  grams.id = "entry-grams";
  gramsLabel.htmlFor = grams.id;
  gramsLabel.appendChild(grams);

  const mealLabel = el("label", "", "Приём пищи");
  const meal = el("select");
  for (const [value, text] of MEALS) {
    const option = el("option", "", text);
    option.value = value;
    meal.appendChild(option);
  }
  meal.value = editing ? editing.meal : "lunch";
  meal.id = "entry-meal";
  mealLabel.htmlFor = meal.id;
  mealLabel.appendChild(meal);

  form.append(gramsLabel, mealLabel);

  const preview = el("div", "preview-box");
  preview.setAttribute("aria-live", "polite");
  form.appendChild(preview);

  function updatePreview() {
    preview.replaceChildren();
    const values = previewOf(selected, Number(grams.value));
    if (!values) {
      preview.hidden = true;
      return;
    }
    preview.hidden = false;
    const list = el("dl");
    for (const [label, value] of [
      ["Ккал", values.kcal],
      ["Белки, г", values.protein],
      ["Жиры, г", values.fat],
      ["Углеводы, г", values.carbs],
    ]) {
      list.appendChild(el("dt", "", label));
      list.appendChild(el("dd", "", String(value)));
    }
    preview.appendChild(el(
      "p", "muted", "Предпросмотр (финальные значения считает сервер)",
    ));
    preview.appendChild(list);
  }
  grams.addEventListener("input", updatePreview);
  updatePreview();

  const submit = el(
    "button", "button-primary",
    editing ? "Сохранить изменения" : "Добавить в дневник",
  );
  submit.type = "submit";
  form.appendChild(submit);
  screen.appendChild(form);
  screen.appendChild(renderNav("add-food"));
  root.replaceChildren(screen);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    errorBox.hidden = true;
    const weight = Number(grams.value);
    if (!selected) {
      errorBox.textContent = "Выберите продукт из поиска";
      errorBox.hidden = false;
      return;
    }
    if (!Number.isFinite(weight) || weight < GRAMS_MIN
        || weight > GRAMS_MAX) {
      errorBox.textContent = `Граммы должны быть от ${GRAMS_MIN} до ${GRAMS_MAX}`;
      errorBox.hidden = false;
      return;
    }
    submit.disabled = true;
    submit.textContent = editing ? "Сохраняем…" : "Добавляем…";
    try {
      if (editing) {
        await store.updateEntry(
          editing.id, { grams: weight, meal: meal.value },
        );
      } else {
        await store.createEntry({
          product_id: selected.id,
          grams: weight,
          meal: meal.value,
          date: localDate(),
        });
      }
      selected = null;
      onDone();
    } catch (error) {
      errorBox.textContent = error.message || "Не удалось сохранить запись";
      errorBox.hidden = false;
      submit.disabled = false;
      submit.textContent = editing ? "Сохранить изменения" : "Добавить в дневник";
    }
  });

  return () => {
    clearTimeout(timer);
  };
}
