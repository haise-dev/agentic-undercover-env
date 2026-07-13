import { create } from "zustand";

export interface AgentConfig {
  name: string;
  color: string;
  provider: string;
  smart_model_name: string;
  fast_model_name: string;
}

export interface SetupState {
  topic: string;
  secretWord: string;
  maxRounds: number;
  agents: AgentConfig[];
  currentStep: number;
  setTopic: (topic: string) => void;
  setSecretWord: (word: string) => void;
  setMaxRounds: (rounds: number) => void;
  updateAgent: (index: number, field: keyof AgentConfig, value: string) => void;
  setStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  reset: () => void;
}

export const DEFAULT_AGENTS: AgentConfig[] = [
  { name: "Alpha", color: "#ef4444", provider: "groq", smart_model_name: "meta-llama/llama-4-scout-17b-16e-instruct", fast_model_name: "llama-3.1-8b-instant" },
  { name: "Beta", color: "#3b82f6", provider: "groq", smart_model_name: "meta-llama/llama-4-scout-17b-16e-instruct", fast_model_name: "llama-3.1-8b-instant" },
  { name: "Gamma", color: "#10b981", provider: "groq", smart_model_name: "meta-llama/llama-4-scout-17b-16e-instruct", fast_model_name: "llama-3.1-8b-instant" },
  { name: "Delta", color: "#f59e0b", provider: "groq", smart_model_name: "meta-llama/llama-4-scout-17b-16e-instruct", fast_model_name: "llama-3.1-8b-instant" },
];

export const useSetupStore = create<SetupState>((set) => ({
  topic: "",
  secretWord: "",
  maxRounds: 3,
  agents: DEFAULT_AGENTS,
  currentStep: 1,
  setTopic: (topic) => set({ topic }),
  setSecretWord: (secretWord) => set({ secretWord }),
  setMaxRounds: (maxRounds) => set({ maxRounds }),
  updateAgent: (index, field, value) => set((state) => {
    const newAgents = [...state.agents];
    newAgents[index] = { ...newAgents[index], [field]: value };
    return { agents: newAgents };
  }),
  setStep: (currentStep) => set({ currentStep }),
  nextStep: () => set((state) => ({ currentStep: Math.min(state.currentStep + 1, 3) })),
  prevStep: () => set((state) => ({ currentStep: Math.max(state.currentStep - 1, 1) })),
  reset: () => set({
    topic: "",
    secretWord: "",
    maxRounds: 3,
    agents: DEFAULT_AGENTS,
    currentStep: 1,
  }),
}));
