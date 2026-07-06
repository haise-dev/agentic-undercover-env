import { useGameStore } from "@/src/lib/store";
import { GameEvent } from "@/src/lib/types";
import { motion, AnimatePresence } from "framer-motion";
import { Trophy, ShieldAlert, Key } from "lucide-react";

export function EndgameCard() {
  const events = useGameStore((state) => state.events as GameEvent[]);
  
  const gameOverEvent = events.find(e => e.event_type === "GAME_OVER");
  if (!gameOverEvent) return null;

  const { result, villager_word, winning_agent_ids, eliminated_agent_id } = gameOverEvent.payload;
  const isImposterWin = result === "imposter_wins";
  
  const imposterId = isImposterWin ? winning_agent_ids?.[0] : eliminated_agent_id;
  const initEvent = events.find(e => e.event_type === "GAME_START");
  const agents = initEvent?.payload.agents || [];
  const imposterName = agents.find((a: any) => a.agent_id === imposterId)?.display_name || "Unknown Agent";

  const reactions = events.filter(e => e.event_type === "SURVIVOR_REACTED");

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 z-50 flex items-center justify-center bg-bg-primary/90 backdrop-blur-sm p-4 overflow-y-auto"
      >
        <motion.div 
          initial={{ scale: 0.8, y: 50 }}
          animate={{ scale: 1, y: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className={`max-w-xl w-full bg-bg-card border-2 rounded-2xl shadow-2xl overflow-hidden my-8 ${
            isImposterWin ? "border-red-500/50 shadow-glow-0 shadow-red-500/20" : "border-emerald-500/50 shadow-glow-0 shadow-emerald-500/20"
          }`}
        >
          <div className={`p-8 text-center flex flex-col items-center border-b ${
            isImposterWin ? "bg-red-500/10 border-red-500/20" : "bg-emerald-500/10 border-emerald-500/20"
          }`}>
            {isImposterWin ? (
              <ShieldAlert className="w-16 h-16 text-red-500 mb-4" />
            ) : (
              <Trophy className="w-16 h-16 text-emerald-500 mb-4" />
            )}
            <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">GAME OVER</h2>
            <p className={`text-2xl font-bold mt-2 ${isImposterWin ? "text-red-400" : "text-emerald-400"}`}>
              {isImposterWin ? "THE IMPOSTER WON!" : "THE VILLAGERS WON!"}
            </p>
            <p className="text-md text-text-muted mt-2">
              The Imposter was <strong className="text-text-primary">{imposterName}</strong>
            </p>
          </div>
          
          <div className="p-8 space-y-6">
            <div className="flex flex-col items-center justify-center p-4 bg-bg-secondary rounded-xl border border-border">
              <Key className="w-6 h-6 text-amber-400 mb-2" />
              <span className="text-sm text-text-muted uppercase tracking-wider mb-1">Villager Word</span>
              <span className="text-2xl font-bold text-text-primary">{villager_word}</span>
            </div>
            
            {reactions.length > 0 && (
              <div className="space-y-3 mt-6">
                <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider text-center border-b border-border pb-2 mb-4">Final Reactions</h3>
                {reactions.map((reaction, idx) => {
                  const agentName = agents.find((a: any) => a.agent_id === reaction.payload.agent_id)?.display_name || "Agent";
                  return (
                    <div key={idx} className="bg-bg-secondary/50 border border-border p-3 rounded-lg text-sm text-text-primary">
                      <strong className="text-text-muted mr-2">{agentName}:</strong>
                      <span className="italic">"{reaction.payload.statement}"</span>
                    </div>
                  );
                })}
              </div>
            )}
            
            <div className="text-center text-text-muted text-sm pt-4">
              <p>The episode has concluded.</p>
              <p className="mt-1">You can review the chat log or start a new game.</p>
            </div>
          </div>
          
          <div className="p-4 bg-bg-secondary border-t border-border text-center">
            <button 
              onClick={() => window.location.href = '/'}
              className="px-6 py-2 bg-text-primary text-bg-primary font-bold rounded-lg hover:bg-text-primary/90 transition-colors"
            >
              Play Again
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
