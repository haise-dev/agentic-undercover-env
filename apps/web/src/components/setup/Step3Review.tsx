"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSetupStore } from "@/src/store/useSetupStore";
import { Button } from "../ui/Button";
import { API_BASE_URL } from "@/src/lib/constants";
import { AlertCircle, ChevronLeft, Play, Loader2 } from "lucide-react";

export function Step3Review() {
  const router = useRouter();
  const { topic, secretWord, maxRounds, agents, prevStep } = useSetupStore();
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleLaunch = async () => {
    setIsLoading(true);
    setErrorMsg("");

    const payload = {
      episode_id: crypto.randomUUID(),
      topic,
      secret_word: secretWord,
      max_rounds: maxRounds,
      agents: agents.map((agent, index) => ({
        agent_id: crypto.randomUUID(),
        display_name: agent.name,
        display_color: agent.color,
        agent_type: "ai",
        llm_config: {
          provider: agent.provider,
          smart_model_name: agent.smart_model_name,
          fast_model_name: agent.fast_model_name,
          temperature: 0.8,
        },
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
        let errorMsg = "Failed to launch game episode.";
        if (Array.isArray(errData.detail)) {
          errorMsg = errData.detail
            .map((e: any) => `${e.loc.join(".")}: ${e.msg}`)
            .join(" | ");
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
    <div className="space-y-6 animate-fade-in">
      <div className="bg-bg-secondary/40 backdrop-blur-md p-6 rounded-2xl border border-border/80 space-y-6">
        <div className="flex items-center space-x-3 border-b border-border pb-4">
          <AlertCircle className="w-6 h-6 text-agent-2" />
          <h3 className="text-xl font-bold text-text-primary">Review & Launch</h3>
        </div>

        {errorMsg && (
          <div className="p-3 text-sm text-red-200 bg-red-500/20 border border-red-500/50 rounded-md">
            {errorMsg}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Game Settings Summary */}
          <div className="md:col-span-1 p-4 rounded-xl bg-bg-primary/30 border border-border/40 space-y-3">
            <h4 className="font-bold text-text-muted text-xs uppercase tracking-wider">
              Game settings
            </h4>
            <div className="space-y-2">
              <div>
                <span className="text-xs text-text-muted block">Topic</span>
                <span className="text-sm font-semibold text-text-primary">{topic}</span>
              </div>
              <div>
                <span className="text-xs text-text-muted block">Secret Word</span>
                <span className="text-sm font-semibold text-text-primary">{secretWord}</span>
              </div>
              <div>
                <span className="text-xs text-text-muted block">Max Rounds</span>
                <span className="text-sm font-semibold text-text-primary">{maxRounds} Rounds</span>
              </div>
            </div>
          </div>

          {/* Agents Config Summary */}
          <div className="md:col-span-2 p-4 rounded-xl bg-bg-primary/30 border border-border/40 space-y-3">
            <h4 className="font-bold text-text-muted text-xs uppercase tracking-wider">
              Agents configuration
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {agents.map((agent, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg bg-bg-secondary/40 border border-border/40 flex items-center space-x-3"
                >
                  <span
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: agent.color }}
                  />
                  <div className="min-w-0">
                    <span className="text-sm font-bold text-text-primary block truncate">
                      {agent.name}
                    </span>
                    <span className="text-xs text-text-muted block truncate">
                      {agent.smart_model_name.split("/").pop()} / {agent.fast_model_name.split("/").pop()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button
          type="button"
          onClick={prevStep}
          variant="secondary"
          disabled={isLoading}
          className="flex items-center space-x-2 border-border/80 hover:bg-bg-secondary"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Back</span>
        </Button>
        <Button
          type="button"
          onClick={handleLaunch}
          disabled={isLoading}
          className="flex items-center space-x-2 px-8 py-3 bg-gradient-to-r from-agent-0 via-agent-1 to-agent-2 text-white shadow-xl shadow-agent-0/20 hover:shadow-agent-0/40 hover:-translate-y-0.5 transition-all duration-200"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Launching...</span>
            </>
          ) : (
            <>
              <span>Launch Episode</span>
              <Play className="w-4 h-4 fill-current" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
