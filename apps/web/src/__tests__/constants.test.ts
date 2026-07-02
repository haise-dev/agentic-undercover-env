import { test } from "node:test";
import assert from "node:assert";

test("API_BASE_URL defaults to http://localhost:8000 when env var not set", async () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;
  delete process.env.NEXT_PUBLIC_API_URL;

  // Use dynamic import with timestamp query to bypass module cache
  const { API_BASE_URL, WS_BASE_URL } = await import(`../lib/constants.ts?t=${Date.now()}`);

  assert.strictEqual(API_BASE_URL, "http://localhost:8000");
  assert.strictEqual(WS_BASE_URL, "ws://localhost:8000");

  if (originalEnv) {
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  }
});

test("WS_BASE_URL replaces http with ws correctly", async () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;
  process.env.NEXT_PUBLIC_API_URL = "http://my-api-server:8000";

  const { API_BASE_URL, WS_BASE_URL } = await import(`../lib/constants.ts?t=${Date.now()}`);

  assert.strictEqual(API_BASE_URL, "http://my-api-server:8000");
  assert.strictEqual(WS_BASE_URL, "ws://my-api-server:8000");

  if (originalEnv) {
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  } else {
    delete process.env.NEXT_PUBLIC_API_URL;
  }
});

test("WS_BASE_URL replaces https with wss correctly", async () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;
  process.env.NEXT_PUBLIC_API_URL = "https://secure-api-server";

  const { API_BASE_URL, WS_BASE_URL } = await import(`../lib/constants.ts?t=${Date.now()}`);

  assert.strictEqual(API_BASE_URL, "https://secure-api-server");
  assert.strictEqual(WS_BASE_URL, "wss://secure-api-server");

  if (originalEnv) {
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  } else {
    delete process.env.NEXT_PUBLIC_API_URL;
  }
});
