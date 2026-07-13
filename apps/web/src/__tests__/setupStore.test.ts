import { test } from "node:test";
import assert from "node:assert";

// Zustand uses client-only stuff, so we might need mock or simple tests.
// Let's test the state manipulation of setup store.
test("useSetupStore state management", async () => {
  const { useSetupStore, DEFAULT_AGENTS } = await import("../store/useSetupStore.ts");
  
  // Verify defaults
  const state = useSetupStore.getState();
  assert.strictEqual(state.topic, "");
  assert.strictEqual(state.secretWord, "");
  assert.strictEqual(state.maxRounds, 3);
  assert.strictEqual(state.currentStep, 1);
  assert.deepStrictEqual(state.agents, DEFAULT_AGENTS);

  // Test setTopic
  useSetupStore.getState().setTopic("History");
  assert.strictEqual(useSetupStore.getState().topic, "History");

  // Test setSecretWord
  useSetupStore.getState().setSecretWord("Napoleon");
  assert.strictEqual(useSetupStore.getState().secretWord, "Napoleon");

  // Test setMaxRounds
  useSetupStore.getState().setMaxRounds(5);
  assert.strictEqual(useSetupStore.getState().maxRounds, 5);

  // Test nextStep/prevStep
  useSetupStore.getState().nextStep();
  assert.strictEqual(useSetupStore.getState().currentStep, 2);

  useSetupStore.getState().prevStep();
  assert.strictEqual(useSetupStore.getState().currentStep, 1);

  // Test updateAgent
  useSetupStore.getState().updateAgent(0, "name", "Agent X");
  assert.strictEqual(useSetupStore.getState().agents[0].name, "Agent X");

  // Test reset
  useSetupStore.getState().reset();
  const resetState = useSetupStore.getState();
  assert.strictEqual(resetState.topic, "");
  assert.strictEqual(resetState.secretWord, "");
  assert.strictEqual(resetState.maxRounds, 3);
  assert.strictEqual(resetState.currentStep, 1);
  assert.strictEqual(resetState.agents[0].name, "Alpha");
});
