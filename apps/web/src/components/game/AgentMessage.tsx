import { useState } from "react";
import { BrainCircuit, MessageCircle } from "lucide-react";

interface AgentMessageProps {
  name: string;
  agentIndex: number;
  content: string;
  innerThought?: string;
}

export function AgentMessage({ name, agentIndex, content, innerThought }: AgentMessageProps) {
  const [showThought, setShowThought] = useState(false);
  const variant = `agent-${agentIndex}`;
  
  return (
    <div className="flex flex-col mb-6 space-y-1 w-full group">
      {/* Name and actions */}
      <div className="flex items-center space-x-2 pl-2">
        <span className={`text-xs font-bold text-${variant}`}>{name}</span>
        {innerThought && (
          <button 
            onClick={() => setShowThought(!showThought)}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-muted hover:text-text-primary flex items-center gap-1"
            title="Toggle Inner Thought"
          >
            <BrainCircuit className="w-3 h-3" />
            <span className="text-[10px] uppercase">Thought</span>
          </button>
        )}
      </div>
      
      {/* Inner thought (conditionally rendered) */}
      {showThought && innerThought && (
        <div className="ml-4 mr-12 mb-2 p-3 text-sm italic text-text-muted bg-bg-secondary/40 border-l-2 border-text-muted rounded-r-md">
          {innerThought}
        </div>
      )}
      
      {/* Main message bubble */}
      <div className={`relative px-4 py-3 text-sm leading-relaxed text-text-primary bg-bg-card/80 backdrop-blur-sm border border-${variant}/30 rounded-2xl rounded-tl-sm shadow-sm inline-block max-w-[85%]`}>
        {content}
      </div>
    </div>
  );
}
