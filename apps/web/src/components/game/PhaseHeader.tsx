import { useGameStore } from "@/src/lib/store";
import { GameEvent } from "@/src/lib/types";
import { useMemo } from "react";
import { Badge } from "../ui/Badge";
import { PlayCircle, MessageSquare, ShieldAlert, Zap, Skull, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function PhaseHeader() {
  const events = useGameStore((state) => state.events as GameEvent[]);
  
  const currentPhase = useMemo(() => {
    if (events.length === 0) return { label: "WAITING FOR START", icon: PlayCircle, color: "text-text-muted" };
    
    // Look at the last non-reaction event to determine phase
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      switch (ev.event_type) {
        case "GAME_START": return { label: "INITIALIZING", icon: Zap, color: "text-agent-0" };
        case "AGENT_SPOKE": return { label: "DISCUSSION PHASE", icon: MessageSquare, color: "text-agent-1" };
        case "VOTE_CAST": return { label: "VOTING PHASE", icon: ShieldAlert, color: "text-agent-2" };
        case "ELIMINATION_RESULT": return { label: "ELIMINATION", icon: Skull, color: "text-agent-3" };
        case "ROLE_REVEAL": return { label: "ROLE REVEAL", icon: PlayCircle, color: "text-agent-0" };
        case "GAME_OVER": return { label: "GAME OVER", icon: CheckCircle, color: "text-agent-0" };
        default: continue;
      }
    }
    return { label: "LIVE", icon: PlayCircle, color: "text-agent-0" };
  }, [events]);

  const { connectionStatus } = useGameStore();
  const StatusIcon = currentPhase.icon;

  return (
    <div className="sticky top-0 z-10 p-4 border-b border-border bg-bg-primary/80 backdrop-blur-xl flex items-center justify-between shadow-sm">
      <AnimatePresence mode="wait">
        <motion.div 
          key={currentPhase.label}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="flex items-center space-x-2"
        >
          <StatusIcon className={`w-5 h-5 ${currentPhase.color}`} />
          <h1 className="text-sm font-semibold tracking-wider text-text-primary uppercase">
            {currentPhase.label}
          </h1>
        </motion.div>
      </AnimatePresence>
      
      <div className="flex items-center space-x-2">
        <div className="flex items-center space-x-1">
          <span className="relative flex h-3 w-3">
            {connectionStatus === "connected" && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span className={`relative inline-flex rounded-full h-3 w-3 ${
              connectionStatus === "connected" ? "bg-emerald-500" :
              connectionStatus === "connecting" ? "bg-amber-500" : "bg-red-500"
            }`}></span>
          </span>
          <span className="text-xs font-medium text-text-muted capitalize hidden sm:inline">
            {connectionStatus}
          </span>
        </div>
      </div>
    </div>
  );
}
