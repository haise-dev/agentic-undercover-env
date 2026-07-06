import { useRef, useEffect } from "react";
import { useGameStore } from "@/src/lib/store";
import { GameEvent } from "@/src/lib/types";
import { AgentMessage } from "./AgentMessage";
import { VoteReveal } from "./VoteReveal";
import { motion, AnimatePresence } from "framer-motion";
import { Info } from "lucide-react";

function getAgentIndex(nameOrId: string, events: GameEvent[]): number {
  const initEvent = events.find(e => e.event_type === "GAME_START");
  if (!initEvent) return 0;
  const agents = initEvent.payload.agents || [];
  const idx = agents.findIndex((a: any) => a.name === nameOrId || a.agent_id === nameOrId);
  return idx !== -1 ? idx : 0;
}

export function ChatFeed() {
  const events = useGameStore((state) => state.events as GameEvent[]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current;
      // Scroll to bottom smoothly
      el.scrollTo({
        top: el.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [events]);

  const chatEvents = events.filter(e => 
    e.event_type === "AGENT_SPOKE" || 
    e.event_type === "VOTE_CAST" || 
    e.event_type === "GAME_START" ||
    e.event_type === "ROLE_REVEAL" ||
    e.event_type === "ELIMINATION_RESULT" ||
    e.event_type === "GAME_ERROR" ||
    e.event_type === "SURVIVOR_REACTED"
  );

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
      <AnimatePresence initial={false}>
        {chatEvents.map((ev, idx) => {
          const key = `${ev.timestamp}-${idx}`;
          
          if (ev.event_type === "GAME_START") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-4"
              >
                <div className="bg-bg-secondary/80 border border-border px-4 py-2 rounded-full text-xs text-text-muted flex items-center space-x-2">
                  <Info className="w-3 h-3" />
                  <span>The game has started. Topic: <strong className="text-text-primary">{ev.payload.topic}</strong></span>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "ROLE_REVEAL") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                className="flex justify-center my-4"
              >
                <div className="bg-amber-500/10 border border-amber-500/30 px-6 py-3 rounded-lg text-sm text-amber-200 text-center">
                  <strong className="block text-amber-400 mb-1">Role Reveal</strong>
                  {ev.payload.agent} was an {ev.payload.role}!
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "VOTE_CAST") {
            const agentIdx = getAgentIndex(ev.payload.voter_agent_id, events);
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const voterName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.voter_agent_id)?.display_name || ev.payload.voter_agent_id;
            const targetName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.target_agent_id)?.display_name || ev.payload.target_agent_id;
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-end my-2"
              >
                <div className={`bg-bg-card/50 border border-agent-${agentIdx}/20 px-4 py-2 rounded-xl text-xs text-text-muted`}>
                  <strong className={`text-agent-${agentIdx}`}>{voterName}</strong> voted to eliminate <strong className="text-text-primary">{targetName}</strong>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "ELIMINATION_RESULT") {
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const agents = initEvent?.payload.agents || [];
            
            const eliminatedName = agents.find((a: any) => a.agent_id === ev.payload.eliminated_agent_id)?.display_name || ev.payload.eliminated_agent_id;
            
            const namedVotes: Record<string, number> = {};
            Object.entries(ev.payload.vote_tally || {}).forEach(([id, count]) => {
              const name = agents.find((a: any) => a.agent_id === id)?.display_name || id;
              namedVotes[name] = count as number;
            });

            return (
              <motion.div key={key}>
                <VoteReveal 
                  eliminatedAgent={eliminatedName} 
                  votes={namedVotes} 
                />
              </motion.div>
            );
          }

          if (ev.event_type === "AGENT_SPOKE") {
            const agentIdx = getAgentIndex(ev.payload.display_name, events);
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
              >
                <AgentMessage
                  name={ev.payload.display_name}
                  agentIndex={agentIdx}
                  content={ev.payload.public_statement}
                  innerThought={ev.payload.inner_thought}
                />
              </motion.div>
            );
          }
          
          if (ev.event_type === "SURVIVOR_REACTED") {
            const agentIdx = getAgentIndex(ev.payload.agent_id, events);
            // We only have the ID, so we need to map to name
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const agentName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.agent_id)?.name || ev.payload.agent_id;
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
              >
                <AgentMessage
                  name={agentName}
                  agentIndex={agentIdx}
                  content={ev.payload.statement}
                />
              </motion.div>
            );
          }

          if (ev.event_type === "GAME_ERROR") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-4"
              >
                <div className="bg-red-500/20 border border-red-500/50 px-4 py-2 rounded-lg text-sm text-red-200">
                  <strong className="block text-red-400 mb-1">Game Engine Error</strong>
                  {ev.payload.error}
                </div>
              </motion.div>
            );
          }

          return null;
        })}
      </AnimatePresence>
    </div>
  );
}
