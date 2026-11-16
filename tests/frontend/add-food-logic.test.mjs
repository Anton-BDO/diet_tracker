import assert from "node:assert/strict";
import test from "node:test";
import { resolveEditing, previewOf } from "../../frontend/js/views/add-food.js";

const DAY = {
  date: "2026-10-20",
  entries: [
    {
      id: "entry-1",
      product_id: "prod-1",
      product_name: "Куриная грудка",
      grams: 150,
      meal: "lunch",
      kcal: 169.5,
      protein: 35.4,
      fat: 2.9,
      carbs: 0.6,
    },
  ],
  totals: { kcal: 169.5, protein: 35.4, fat: 2.9, carbs: 0.6 },
  norm: { kcal: 2345, protein: 176, fat: 78, carbs: 235 },
  remaining: { kcal: 2175.5, protein: 140.6, fat: 75.1, carbs: 234.4 },
  is_success: false,
};

test("resolveEditing: no id means create mode", () => {
  assert.deepEqual(resolveEditing(null, DAY), { status: "create" });
  assert.deepEqual(resolveEditing("", DAY), { status: "create" });
});

test("resolveEditing: without day summary waits for loading", () => {
  assert.deepEqual(resolveEditing("entry-1", null), { status: "loading" });
});

test("resolveEditing: known entry opens editor", () => {
  const result = resolveEditing("entry-1", DAY);
  assert.equal(result.status, "edit");
  assert.equal(result.entry.id, "entry-1");
});

test("resolveEditing: unknown entry is reported as missing", () => {
  assert.deepEqual(resolveEditing("nope", DAY), { status: "missing" });
});

const PRODUCT = { kcal: 113, protein: 23.6, fat: 1.9, carbs: 0.4 };

test("previewOf scales nutrients to grams", () => {
  assert.deepEqual(previewOf(PRODUCT, 250), {
    kcal: 282.5, protein: 59.0, fat: 4.8, carbs: 1.0,
  });
});

test("previewOf returns null for edit-mode stub without nutrients", () => {
  const editStub = { id: "prod-1", name: "Куриная грудка" };
  assert.equal(previewOf(editStub, 250), null);
  assert.equal(previewOf(null, 250), null);
});

test("previewOf rejects grams outside allowed range", () => {
  assert.equal(previewOf(PRODUCT, 0), null);
  assert.equal(previewOf(PRODUCT, Number("abc")), null);
});
