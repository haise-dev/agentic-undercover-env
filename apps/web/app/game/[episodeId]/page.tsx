"use client";

import { useEffect, useRef } from "react";
import { use } from "react";
import { AppShell } from "@/src/components/layout/AppShell";
import { AgentRoster } from "@/src/components/game/AgentRoster";
import { PhaseHeader } from "@/src/components/game/PhaseHeader";
import { ChatFeed } from "@/src/components/game/ChatFeed";
import { EndgameCard } from "@/src/components/game/EndgameCard";
import { useGameStream } from "@/src/lib/useGameStream";
import { API_BASE_URL } from "@/src/lib/constants";
import { useGameStore } from "@/src/lib/store";

export default function GamePage({ params }: { params: Promise<{ episodeId: string }> }) {
  const { episodeId } = use(params);
  
  const { connectionStatus } = useGameStream(episodeId);
  const events = useGameStore((state) => state.events);
  const startTriggered = useRef(false);

  // Trigger game start API once connection is established
  useEffect(() => {
    if (connectionStatus === "connected" && !startTriggered.current) {
      // If we don't have any INIT event, it's a brand new game
      const hasInit = events.some(e => e.event_type === "INIT");
      if (!hasInit) {
        startTriggered.current = true;
        fetch(`${API_BASE_URL}/api/episodes/${episodeId}/start`, {
          method: "POST"
        }).catch(err => console.error("Failed to start episode:", err));
      }
    }
  }, [connectionStatus, episodeId, events]);

  return (
    <div className="relative">
      <EndgameCard />
      
      <AppShell sidebar={<AgentRoster />}>
        <div className="flex flex-col h-[calc(100vh-2rem)] md:h-[calc(100vh-3rem)] rounded-xl overflow-hidden border border-border shadow-2xl bg-bg-primary">
          <PhaseHeader />
          <ChatFeed />
        </div>
      </AppShell>
    </div>
  );
}
