"use client";

import { useRef, useEffect, useState } from "react";
import { useGameStore } from "@/src/lib/store";
import { GameEvent } from "@/src/lib/types";
import { AgentMessage } from "./AgentMessage";
import { VoteReveal } from "./VoteReveal";
import { motion, AnimatePresence } from "framer-motion";
import { Info, BrainCircuit } from "lucide-react";

function getAgentIndex(nameOrId: string, events: GameEvent[]): number {
  const initEvent = events.find(e => e.event_type === "GAME_START");
  if (!initEvent) return 0;
  const agents = initEvent.payload.agents || [];
  const idx = agents.findIndex((a: any) => a.display_name === nameOrId || a.agent_id === nameOrId);
  return idx !== -1 ? idx : 0;
}

function TypingBubble({ name, agentIndex }: { name: string; agentIndex: number }) {
  const variant = `agent-${agentIndex}`;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center space-x-2 pl-4 py-2"
    >
      <span className={`text-xs font-bold text-${variant}`}>{name}</span>
      <div className="flex items-center space-x-1.5 bg-bg-secondary/60 border border-border px-3.5 py-2 rounded-2xl rounded-tl-sm shadow-sm">
        <span className="text-text-muted text-[11px]">thinking...</span>
        <span className="flex space-x-1 pt-1">
          <span className="w-1 h-1 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1 h-1 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1 h-1 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </span>
      </div>
    </motion.div>
  );
}

export function ChatFeed() {
  const events = useGameStore((state) => state.events as GameEvent[]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [visibleEvents, setVisibleEvents] = useState<GameEvent[]>([]);
  const [typingAgent, setTypingAgent] = useState<{ name: string; index: number } | null>(null);

  const processedEventsCount = useRef(0);
  const eventQueue = useRef<GameEvent[]>([]);
  const isProcessing = useRef(false);
  const mounted = useRef(true);
  const isInitialMount = useRef(true);

  // Filter events related to the main chat feed
  const chatEvents = events.filter(e => 
    e.event_type === "ROUND_STARTED" ||
    e.event_type === "POLLING_STARTED" ||
    e.event_type === "POLL_RESULT" ||
    e.event_type === "VOTING_STARTED" ||
    e.event_type === "AGENT_SPOKE" || 
    e.event_type === "AGENT_DELIBERATED" || 
    e.event_type === "VOTE_CAST" || 
    e.event_type === "GAME_START" ||
    e.event_type === "ROLE_REVEAL" ||
    e.event_type === "ELIMINATION_RESULT" ||
    e.event_type === "GAME_ERROR" ||
    e.event_type === "SURVIVOR_REACTED"
  );

  // Set up unmount tracking
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Process queue sequentially with stagger delays
  const processQueue = async () => {
    if (isProcessing.current) return;
    isProcessing.current = true;

    while (eventQueue.current.length > 0) {
      if (!mounted.current) break;
      const nextEvent = eventQueue.current[0];

      // If it is a dialogue event or vote cast event, show the typing bubble
      if (
        nextEvent.event_type === "AGENT_SPOKE" ||
        nextEvent.event_type === "AGENT_DELIBERATED" ||
        nextEvent.event_type === "SURVIVOR_REACTED" ||
        nextEvent.event_type === "VOTE_CAST"
      ) {
        let display_name = "";
        if (nextEvent.event_type === "SURVIVOR_REACTED") {
          const currentEvents = useGameStore.getState().events as GameEvent[];
          const initEvent = currentEvents.find(e => e.event_type === "GAME_START");
          display_name = initEvent?.payload.agents?.find((a: any) => a.agent_id === nextEvent.payload.agent_id)?.display_name || nextEvent.payload.agent_id;
        } else if (nextEvent.event_type === "VOTE_CAST") {
          const currentEvents = useGameStore.getState().events as GameEvent[];
          const initEvent = currentEvents.find(e => e.event_type === "GAME_START");
          display_name = initEvent?.payload.agents?.find((a: any) => a.agent_id === nextEvent.payload.voter_agent_id)?.display_name || nextEvent.payload.voter_agent_id;
        } else {
          display_name = nextEvent.payload.display_name;
        }

        const currentEvents = useGameStore.getState().events as GameEvent[];
        const agentIdx = getAgentIndex(display_name, currentEvents);

        if (mounted.current) {
          setTypingAgent({ name: display_name, index: agentIdx });
        }

        // 2-second typing delay
        await new Promise((resolve) => setTimeout(resolve, 2000));

        if (mounted.current) {
          setTypingAgent(null);
        }
      }

      if (mounted.current) {
        setVisibleEvents((prev) => [...prev, nextEvent]);
      }

      eventQueue.current.shift();
    }

    isProcessing.current = false;
  };

  // Collect new events and trigger queue processing
  useEffect(() => {
    if (isInitialMount.current) {
      // Pour existing events immediately for initial catchup/reconnects
      isInitialMount.current = false;
      setVisibleEvents(chatEvents);
      processedEventsCount.current = chatEvents.length;
      return;
    }

    const newEvents = chatEvents.slice(processedEventsCount.current);
    if (newEvents.length > 0) {
      eventQueue.current = [...eventQueue.current, ...newEvents];
      processedEventsCount.current = chatEvents.length;
      processQueue();
    }
  }, [chatEvents]);

  // Smooth auto-scroll when visible messages list or typing status changes
  useEffect(() => {
    if (scrollRef.current) {
      const el = scrollRef.current;
      el.scrollTo({
        top: el.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [visibleEvents, typingAgent]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
      <AnimatePresence initial={false}>
        {visibleEvents.map((ev, idx) => {
          const key = `${ev.timestamp}-${idx}`;

          if (ev.event_type === "GAME_START") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-4"
              >
                <div className="bg-bg-secondary/80 border border-border px-5 py-2.5 rounded-full text-xs text-text-muted flex items-center space-x-2">
                  <Info className="w-3.5 h-3.5 text-agent-0" />
                  <span>The game has started. Topic: <strong className="text-text-primary">{ev.payload.topic}</strong></span>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "ROUND_STARTED") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-6"
              >
                <div className="bg-agent-0/10 border border-agent-0/30 px-5 py-2.5 rounded-full text-xs font-black text-agent-0 uppercase tracking-widest flex items-center space-x-2 shadow-sm">
                  <span>Round {ev.payload.round_number}: Word Guessing Phase</span>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "POLLING_STARTED") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-6"
              >
                <div className="bg-bg-secondary border border-border/80 px-5 py-2.5 rounded-full text-xs text-text-muted flex items-center space-x-2 animate-pulse shadow-sm">
                  <BrainCircuit className="w-3.5 h-3.5 text-amber-400 animate-spin" style={{ animationDuration: '3s' }} />
                  <span>The village is deciding whether to proceed to a vote...</span>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "ROLE_REVEAL") {
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const agentName = initEvent?.payload.agents?.find(a => a.agent_id === ev.payload.agent_id)?.display_name || ev.payload.agent_id;
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                className="flex justify-center my-4"
              >
                <div className="bg-amber-500/10 border border-amber-500/30 px-6 py-3.5 rounded-xl text-sm text-amber-200 text-center max-w-md">
                  <strong className="block text-amber-400 mb-1">Role Reveal</strong>
                  {agentName} was an {ev.payload.role}!
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "VOTING_STARTED") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
                className="flex justify-center my-6"
              >
                <div className="bg-red-950/10 border border-red-900/30 px-5 py-2.5 rounded-full text-xs text-red-300 flex items-center space-x-2 animate-pulse shadow-sm">
                  <BrainCircuit className="w-3.5 h-3.5 text-red-500 animate-spin" style={{ animationDuration: '3s' }} />
                  <span>The village is casting their secret votes...</span>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "VOTE_CAST") {
            const agentIdx = getAgentIndex(ev.payload.voter_agent_id, events);
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const voterName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.voter_agent_id)?.display_name || ev.payload.voter_agent_id;
            const targetName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.target_agent_id)?.display_name || ev.payload.target_agent_id;
            const variant = `agent-${agentIdx}`;
            
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                className="flex flex-col mb-6 space-y-1.5 w-full"
              >
                {/* Voter identity */}
                <div className="flex items-center space-x-2 pl-2">
                  <span className={`text-[11px] font-black uppercase tracking-wider text-${variant}`}>{voterName} (Voting)</span>
                </div>

                {/* Monologue / Inner Thought */}
                {ev.payload.inner_thought && (
                  <div className="ml-4 mr-12 mb-1 p-3 text-sm italic text-text-muted bg-bg-secondary/40 border-l-2 border-red-500/50 rounded-r-md">
                    "{ev.payload.inner_thought}"
                  </div>
                )}

                {/* Vote Bubble */}
                <div className="relative px-4 py-3 text-sm font-semibold text-text-primary bg-red-950/20 backdrop-blur-sm border border-red-500/30 rounded-2xl rounded-tl-sm shadow-sm inline-block max-w-[85%]">
                  👉 Quyết định bỏ phiếu loại: <strong className="text-red-400 font-extrabold">{targetName}</strong>
                </div>
              </motion.div>
            );
          }

          if (ev.event_type === "POLL_RESULT") {
            return (
              <motion.div 
                key={key}
                initial={{ opacity: 0, y: 15 }} 
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center space-y-4 my-6"
              >
                <div className="bg-bg-secondary border border-border px-4 py-3 rounded-xl text-xs text-text-muted flex flex-col items-center gap-1.5 shadow-sm max-w-xs text-center">
                  <span className="font-bold text-text-primary text-[11px] uppercase tracking-wider">Poll Results</span>
                  <span>Vote Now: <strong className="text-emerald-400">{ev.payload.vote_now_count}</strong> · Skip: <strong className="text-amber-400">{ev.payload.skip_count}</strong></span>
                  {ev.payload.forced && <span className="text-[10px] text-red-400 uppercase tracking-widest font-extrabold animate-pulse">Max rounds reached: Forced voting</span>}
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

          if (ev.event_type === "AGENT_SPOKE" || ev.event_type === "AGENT_DELIBERATED") {
            const agentIdx = getAgentIndex(ev.payload.display_name, events);
            const isDelib = ev.event_type === "AGENT_DELIBERATED";
            const isFirstDelib = isDelib && (idx === 0 || visibleEvents[idx - 1].event_type !== "AGENT_DELIBERATED");

            return (
              <div key={key} className="space-y-4">
                {isFirstDelib && (
                  <motion.div 
                    initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
                    className="flex justify-center my-6"
                  >
                    <div className="bg-agent-1/10 border border-agent-1/30 px-5 py-2.5 rounded-full text-xs font-black text-agent-1 uppercase tracking-widest flex items-center space-x-2 shadow-sm">
                      <span>Round {ev.payload.round_number}: Deliberation Phase</span>
                    </div>
                  </motion.div>
                )}
                <motion.div
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
              </div>
            );
          }
          
          if (ev.event_type === "SURVIVOR_REACTED") {
            const agentIdx = getAgentIndex(ev.payload.agent_id, events);
            const initEvent = events.find(e => e.event_type === "GAME_START");
            const agentName = initEvent?.payload.agents?.find((a: any) => a.agent_id === ev.payload.agent_id)?.display_name || ev.payload.agent_id;
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
        {typingAgent && (
          <TypingBubble key="typing-bubble" name={typingAgent.name} agentIndex={typingAgent.index} />
        )}
      </AnimatePresence>
    </div>
  );
}
