"use client";

import { useEffect, useState, useMemo } from "react";
import { useGameStore } from "@/src/lib/store";
import { GameEvent } from "@/src/lib/types";
import { API_BASE_URL } from "@/src/lib/constants";
import { Cpu } from "lucide-react";

interface QuotaUsage {
  api_key_index: number;
  total_tokens: number;
}

export function APIMonitor() {
  const [usages, setUsages] = useState<QuotaUsage[]>([]);
  const [isUpdating, setIsUpdating] = useState(false);
  const events = useGameStore((state) => state.events as GameEvent[]);

  // Dynamically map API key index to Agent display name
  const agentNames = useMemo(() => {
    let roster: string[] = ["Alpha", "Beta", "Gamma", "Delta"];
    events.forEach((ev) => {
      if (ev.event_type === "GAME_START" && ev.payload.agents) {
        roster = ev.payload.agents.map((a) => a.display_name);
      }
    });
    return roster;
  }, [events]);

  useEffect(() => {
    let active = true;
    async function fetchQuota() {
      setIsUpdating(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/quota`);
        if (!res.ok) throw new Error("Failed to load quota");
        const data = await res.json();
        if (active) {
          setUsages(data);
        }
      } catch (err) {
        console.error("Quota fetch failed:", err);
      } finally {
        if (active) {
          setTimeout(() => setIsUpdating(false), 600);
        }
      }
    }

    fetchQuota();
    const interval = setInterval(fetchQuota, 4000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="bg-bg-card/30 backdrop-blur-md border border-border/50 rounded-xl p-4 space-y-4 shadow-lg mt-auto">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-agent-1 animate-pulse" />
          <h3 className="text-xs font-bold tracking-wider text-text-primary uppercase">
            API Key Monitor
          </h3>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[9px] text-text-muted font-mono uppercase">
            {isUpdating ? "Syncing" : "Live"}
          </span>
          <span className="relative flex h-1.5 w-1.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75 ${isUpdating ? "duration-300" : ""}`}></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500"></span>
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {usages.map((usage) => {
          const agentName = agentNames[usage.api_key_index - 1] || `Agent ${usage.api_key_index}`;
          const agentColorClass = `text-agent-${usage.api_key_index - 1}`;
          
          return (
            <div key={usage.api_key_index} className="space-y-1">
              <div className="flex justify-between items-center text-[11px]">
                <span className="font-semibold text-text-muted">
                  Key #{usage.api_key_index} ({agentName})
                </span>
                <span className={`font-mono font-bold ${agentColorClass} transition-all duration-500`}>
                  {usage.total_tokens.toLocaleString()} tkn
                </span>
              </div>
              <div className="w-full bg-bg-primary/50 h-1 rounded-full overflow-hidden border border-border/30">
                <div
                  className={`h-full bg-gradient-to-r from-agent-${usage.api_key_index - 1} to-agent-${usage.api_key_index - 1}/70 transition-all duration-500`}
                  style={{ width: `${Math.min((usage.total_tokens / 100000) * 100, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
        {usages.length === 0 && (
          <p className="text-xs text-text-muted italic text-center py-2">
            No active API usage tracked yet.
          </p>
        )}
      </div>
    </div>
  );
}
