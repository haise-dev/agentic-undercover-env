import { motion } from "framer-motion";
import { Skull } from "lucide-react";

interface VoteRevealProps {
  eliminatedAgent: string;
  votes: Record<string, number>;
}

export function VoteReveal({ eliminatedAgent, votes }: VoteRevealProps) {
  return (
    <div className="flex justify-center my-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 20 }}
        className="bg-bg-card border border-red-500/30 rounded-xl overflow-hidden shadow-glow-0 shadow-red-500/20 max-w-md w-full"
      >
        <div className="bg-red-500/10 p-4 border-b border-red-500/20 flex flex-col items-center justify-center">
          <Skull className="w-8 h-8 text-red-400 mb-2" />
          <h3 className="text-lg font-bold text-red-50 text-center">Elimination Result</h3>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex justify-between items-center text-sm font-medium text-text-muted pb-2 border-b border-border">
            <span>Candidate</span>
            <span>Votes Received</span>
          </div>
          {Object.entries(votes).map(([target, count]) => (
            <div key={target} className="flex justify-between items-center text-sm">
              <span className={target === eliminatedAgent ? "text-red-400 font-bold" : "text-text-primary"}>
                {target}
              </span>
              <span className="text-text-muted">
                {count} {count === 1 ? 'vote' : 'votes'}
              </span>
            </div>
          ))}
          <div className="pt-4 mt-2 border-t border-border text-center">
            <span className="text-lg font-bold text-text-primary">{eliminatedAgent}</span>
            <span className="text-text-muted ml-2">was eliminated by majority vote.</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
