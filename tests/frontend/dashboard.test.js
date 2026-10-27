import assert from "node:assert/strict";
import test from "node:test";
import { createApiClient } from "../../frontend/js/api.js";

test("daySummary makes a GET request to /diary with the given date", async () => {
  const calls = [];
  
  const client = createApiClient({
    fetchImpl: async (url, options) => {
      calls.push({ url, ...options });
      return new Response(JSON.stringify({ totals: { kcal: 2000 } }));
    }
  });

  const testDate = "2026-10-20";
  
  await client.daySummary(testDate);

  assert.equal(calls.length, 1);
  
  assert.equal(calls[0].url, `/api/diary?date=${testDate}`);
  
  assert.equal(calls[0].method, "GET");
});
