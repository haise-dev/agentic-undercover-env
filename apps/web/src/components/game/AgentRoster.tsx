import { useGameStore } from "@/src/lib/store";
import { Badge } from "../ui/Badge";
import { UserCircle, Skull } from "lucide-react";
import { useMemo } from "react";
import { GameEvent } from "@/src/lib/types";
import { APIMonitor } from "./APIMonitor";

// Extract agents dynamically from INIT event, and update status from ELIMINATION_RESULT
export function AgentRoster() {
  const events = useGameStore((state) => state.events as GameEvent[]);
  
  const agents = useMemo(() => {
    let roster: { name: string; is_eliminated: boolean; id?: string; role?: string; }[] = [
      { name: "Alpha", is_eliminated: false },
      { name: "Beta", is_eliminated: false },
      { name: "Gamma", is_eliminated: false },
      { name: "Delta", is_eliminated: false },
    ];
    
    // Process events chronologically to build current state
    events.forEach((ev) => {
      if (ev.event_type === "GAME_START" && ev.payload.agents) {
        roster = ev.payload.agents.map((a) => ({ 
          name: a.display_name, 
          id: a.agent_id, 
          role: a.role,
          is_eliminated: false 
        }));
      }
      if (ev.event_type === "ELIMINATION_RESULT") {
        const idx = roster.findIndex((a: any) => a.id === ev.payload.eliminated_agent_id);
        if (idx !== -1) roster[idx].is_eliminated = true;
      }
    });
    
    return roster;
  }, [events]);

  return (
    <div className="flex flex-col h-full w-full p-4 space-y-6">
      <div className="pb-4 border-b border-border">
        <h2 className="text-xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-agent-0 to-agent-1">
          Agent Roster
        </h2>
      </div>
      
      <div className="flex-1 space-y-4">
        {agents.map((agent, index) => {
          const variant = `agent-${index}` as any;
          return (
            <div
              key={agent.name}
              className={`flex items-center justify-between p-3 rounded-lg border transition-all duration-300 ${
                agent.is_eliminated 
                  ? "bg-bg-secondary/50 border-border opacity-50 grayscale" 
                  : `bg-bg-card/50 border-${variant}/30 shadow-sm`
              }`}
            >
              <div className="flex items-center space-x-3">
                {agent.is_eliminated ? (
                  <Skull className="w-8 h-8 text-text-muted" />
                ) : (
                  <UserCircle className={`w-8 h-8 text-agent-${index}`} />
                )}
                <div>
                  <div className={`font-medium ${agent.is_eliminated ? "line-through text-text-muted" : "text-text-primary"}`}>
                    {agent.name}
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {!agent.is_eliminated ? (
                      <Badge variant={variant} className="text-[10px]">Alive</Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px]">Eliminated</Badge>
                    )}
                    {agent.role === "imposter" && (
                      <Badge variant="outline" className="text-[10px] bg-red-500/20 text-red-400 border-red-500/30">Imposter</Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      <APIMonitor />
    </div>
  );
}
