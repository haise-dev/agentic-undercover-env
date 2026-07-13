"use client";

import { useEffect, useRef } from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/src/components/layout/AppShell";
import { AgentRoster } from "@/src/components/game/AgentRoster";
import { PhaseHeader } from "@/src/components/game/PhaseHeader";
import { ChatFeed } from "@/src/components/game/ChatFeed";
import { EndgameCard } from "@/src/components/game/EndgameCard";
import { useGameStream } from "@/src/lib/useGameStream";
import { API_BASE_URL } from "@/src/lib/constants";
import { useGameStore } from "@/src/lib/store";
import { APIMonitor } from "@/src/components/game/APIMonitor";

export default function GamePage({ params }: { params: Promise<{ episodeId: string }> }) {
  const { episodeId } = use(params);
  const router = useRouter();
  
  const { connectionStatus } = useGameStream(episodeId);
  const events = useGameStore((state) => state.events);
  const startTriggered = useRef(false);

  // Trigger game start API once connection is established
  useEffect(() => {
    if (connectionStatus === "connected" && !startTriggered.current) {
      // If we don't have any INIT event, it's a brand new game
      const hasStart = events.some(e => e.event_type === "GAME_START");
      if (!hasStart) {
        startTriggered.current = true;
        fetch(`${API_BASE_URL}/api/episodes/${episodeId}/start`, {
          method: "POST"
        }).catch(err => console.error("Failed to start episode:", err));
      }
    }
  }, [connectionStatus, episodeId, events]);

  // Redirect to Setup page (/) on GAME_ERROR after 4 seconds
  const hasError = events.some(e => e.event_type === "GAME_ERROR");
  useEffect(() => {
    if (hasError) {
      const timer = setTimeout(() => {
        router.push("/");
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [hasError, router]);

  return (
    <div className="relative">
      <EndgameCard />
      
      <AppShell sidebar={<AgentRoster />}>
        <div className="flex flex-col h-[calc(100vh-2rem)] md:h-[calc(100vh-3rem)] rounded-xl overflow-hidden border border-border shadow-2xl bg-bg-primary">
          <PhaseHeader />
          <ChatFeed />
        </div>
      </AppShell>

      <div className="block md:hidden mt-6 px-4 pb-8">
        <APIMonitor />
      </div>
    </div>
  );
}

