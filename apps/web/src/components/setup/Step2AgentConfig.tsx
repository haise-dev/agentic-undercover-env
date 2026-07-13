"use client";

import { useEffect, useState } from "react";
import { useSetupStore, AgentConfig } from "@/src/store/useSetupStore";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { API_BASE_URL } from "@/src/lib/constants";
import { Users, AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

interface ProviderInfo {
  provider: string;
  models: string[];
  is_exhausted: boolean;
}

export function Step2AgentConfig() {
  const { agents, updateAgent, prevStep, nextStep } = useSetupStore();
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let active = true;
    async function fetchProviders() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/providers`);
        if (!res.ok) throw new Error("Failed to load providers list");
        const data = await res.json();
        if (active) {
          setProviders(data);
          setIsLoading(false);
        }
      } catch (err: any) {
        if (active) {
          setErrorMsg(err.message || "Could not reach API server.");
          setIsLoading(false);
        }
      }
    }
    fetchProviders();
    return () => {
      active = false;
    };
  }, []);

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    // Validate all agents are filled
    const allValid = agents.every(
      (agent) => agent.name.trim() && agent.provider && agent.smart_model_name && agent.fast_model_name
    );
    if (allValid) {
      nextStep();
    }
  };

  if (isLoading) {
    return (
      <div className="bg-bg-secondary/40 backdrop-blur-md p-12 rounded-2xl border border-border/80 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-agent-0" />
        <p className="text-text-muted">Loading supported model configurations...</p>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className="bg-bg-secondary/40 backdrop-blur-md p-8 rounded-2xl border border-border/80 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto" />
        <p className="text-red-400 font-medium">{errorMsg}</p>
        <Button onClick={() => window.location.reload()} variant="secondary">
          Retry Connection
        </Button>
      </div>
    );
  }

  const groqProvider = providers.find((p) => p.provider === "groq");
  const isGroqExhausted = groqProvider?.is_exhausted || false;

  return (
    <form onSubmit={handleNext} className="space-y-6 animate-fade-in">
      <div className="bg-bg-secondary/40 backdrop-blur-md p-6 rounded-2xl border border-border/80 space-y-6">
        <div className="flex items-center space-x-3 border-b border-border pb-4">
          <Users className="w-6 h-6 text-agent-1" />
          <h3 className="text-xl font-bold text-text-primary">Configure Agents</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {agents.map((agent, idx) => {
            return (
              <div
                key={idx}
                className="p-5 rounded-xl bg-bg-primary/40 border border-border/60 hover:border-border transition-all duration-200 space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <span
                      className="w-3.5 h-3.5 rounded-full shadow-md"
                      style={{ backgroundColor: agent.color }}
                    />
                    <h4 className="font-bold text-text-muted text-sm uppercase tracking-wider">
                      Agent #{idx + 1}
                    </h4>
                  </div>
                </div>

                <div className="space-y-3">
                  {/* Name Input */}
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-text-muted uppercase">
                      Name
                    </label>
                    <Input
                      value={agent.name}
                      onChange={(e) => updateAgent(idx, "name", e.target.value)}
                      required
                      placeholder={`Name for Agent ${idx + 1}`}
                      className="bg-bg-primary/60 border-border/40 focus:ring-agent-1/50"
                    />
                  </div>

                  {/* Model Tiering Configuration */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-text-muted uppercase flex items-center gap-1">
                        Smart Model
                        {isGroqExhausted && (
                          <AlertTriangle className="w-3.5 h-3.5 text-red-500 animate-pulse" />
                        )}
                      </label>
                      <select
                        value={agent.smart_model_name}
                        onChange={(e) => updateAgent(idx, "smart_model_name", e.target.value)}
                        className="w-full bg-bg-primary/60 border border-border/60 rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-agent-1/50"
                      >
                        <option value="meta-llama/llama-4-scout-17b-16e-instruct" className="bg-bg-primary">
                          Llama-4-scout-17b
                        </option>
                        <option value="llama-3.3-70b-versatile" className="bg-bg-primary">
                          Llama-3.3-70b
                        </option>
                        <option value="openai/gpt-oss-120b" className="bg-bg-primary">
                          GPT-OSS-120b
                        </option>
                        <option value="qwen/qwen3.6-27b" className="bg-bg-primary">
                          Qwen-3.6-27b
                        </option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-text-muted uppercase">
                        Fast Model
                      </label>
                      <div className="w-full bg-bg-primary/30 border border-border/40 rounded-lg px-3 py-2 text-text-muted text-sm font-medium">
                        Llama-8b
                      </div>
                    </div>
                  </div>

                  {/* Quota Exhausted Warning Banner */}
                  {isGroqExhausted && (
                    <div className="p-3 bg-red-950/30 border border-red-500/30 rounded-lg flex items-start gap-2.5">
                      <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <p className="text-xs text-red-300 leading-normal">
                        <strong>Warning:</strong> GROQ provider is marked as rate-limited/exhausted. Starting this game might result in rate limit failures.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button
          type="button"
          onClick={prevStep}
          variant="secondary"
          className="flex items-center space-x-2 border-border/80 hover:bg-bg-secondary"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Back</span>
        </Button>
        <Button
          type="submit"
          variant="agent-0"
          className="flex items-center space-x-2 bg-gradient-to-r from-agent-1 to-agent-2 text-white shadow-lg hover:shadow-agent-1/30 hover:-translate-y-0.5 transition-all duration-200"
        >
          <span>Continue</span>
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </form>
  );
}
