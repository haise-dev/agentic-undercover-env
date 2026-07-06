"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/src/lib/constants";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/Card";
import { Input } from "./ui/Input";
import { Select } from "./ui/Select";
import { Button } from "./ui/Button";

interface AgentConfig {
  name: string;
  provider: string;
  model_name: string;
}

const DEFAULT_AGENTS: AgentConfig[] = [
  { name: "Alpha", provider: "groq", model_name: "llama-3.3-70b-versatile" },
  { name: "Beta", provider: "groq", model_name: "llama-3.3-70b-versatile" },
  { name: "Gamma", provider: "groq", model_name: "llama-3.1-8b-instant" },
  { name: "Delta", provider: "groq", model_name: "llama-3.1-8b-instant" },
];

const PROVIDER_MODELS = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
  gemini: ["gemini-3.5-flash", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
  deepseek: ["deepseek-chat", "deepseek-coder"],
};

export function SetupForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [secretWord, setSecretWord] = useState("");
  const [agents, setAgents] = useState<AgentConfig[]>(DEFAULT_AGENTS);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleAgentChange = (index: number, field: keyof AgentConfig, value: string) => {
    const newAgents = [...agents];
    newAgents[index] = { ...newAgents[index], [field]: value };
    setAgents(newAgents);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic || !secretWord) {
      setErrorMsg("Topic and Secret Word are required.");
      return;
    }
    setErrorMsg("");
    setIsLoading(true);

    const COLORS = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b"];
    const payload = {
      episode_id: crypto.randomUUID(),
      topic,
      secret_word: secretWord,
      agents: agents.map((agent, index) => ({
        agent_id: crypto.randomUUID(),
        display_name: agent.name,
        display_color: COLORS[index % COLORS.length],
        agent_type: "ai",
        llm_config: {
          provider: agent.provider,
          model_name: agent.model_name,
        }
      })),
    };

    try {
      const res = await fetch(`${API_BASE_URL}/api/episodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        let errorMsg = "Failed to create episode";
        if (Array.isArray(errData.detail)) {
          errorMsg = errData.detail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join(' | ');
        } else if (errData.detail) {
          errorMsg = errData.detail;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      if (data.episode_id) {
        router.push(`/game/${data.episode_id}`);
      } else {
        throw new Error("Invalid response from server: Missing episode_id");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error while connecting to server.");
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-xl">
      <CardHeader className="border-b border-border mb-6">
        <CardTitle className="text-2xl text-agent-0">Configure New Episode</CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-8">
          {errorMsg && (
            <div className="p-3 text-sm text-red-200 bg-red-500/20 border border-red-500/50 rounded-md">
              {errorMsg}
            </div>
          )}

          {/* Game Settings */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-text-primary">Game Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm text-text-muted font-medium">Discussion Topic</label>
                <Input
                  placeholder="e.g., Programming Languages"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-text-muted font-medium">Secret Word (for Imposter)</label>
                <Input
                  placeholder="e.g., Python"
                  value={secretWord}
                  onChange={(e) => setSecretWord(e.target.value)}
                  required
                />
              </div>
            </div>
          </div>

          {/* Agent Settings */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-text-primary">Agent Roster (4 Players)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {agents.map((agent, idx) => (
                <div key={idx} className="p-4 rounded-lg bg-bg-secondary border border-border space-y-3">
                  <h4 className="font-medium text-sm text-text-muted">Agent {idx + 1}</h4>
                  
                  <div className="space-y-2">
                    <label className="text-xs text-text-muted">Display Name</label>
                    <Input
                      value={agent.name}
                      onChange={(e) => handleAgentChange(idx, "name", e.target.value)}
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">Provider</label>
                      <Select 
                        value={agent.provider} 
                        onChange={(e) => {
                          const newProvider = e.target.value;
                          const newModel = PROVIDER_MODELS[newProvider as keyof typeof PROVIDER_MODELS][0];
                          handleAgentChange(idx, "provider", newProvider);
                          handleAgentChange(idx, "model_name", newModel);
                        }}
                      >
                        <option value="openai">OpenAI</option>
                        <option value="gemini">Gemini</option>
                        <option value="groq">Groq</option>
                        <option value="deepseek">DeepSeek</option>
                      </Select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-text-muted mb-1.5 uppercase tracking-wider">Model Name</label>
                      <Select 
                        value={agent.model_name}
                        onChange={(e) => handleAgentChange(idx, "model_name", e.target.value)}
                      >
                        {PROVIDER_MODELS[agent.provider as keyof typeof PROVIDER_MODELS].map((model) => (
                          <option key={model} value={model}>{model}</option>
                        ))}
                      </Select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <Button
              type="submit"
              variant="agent-0"
              size="lg"
              disabled={isLoading || !topic || !secretWord}
              className="w-full md:w-auto"
            >
              {isLoading ? "Starting Game..." : "Launch Episode"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
