import { create } from "zustand";

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export interface GameEvent {
  event_type: string;
  timestamp: string;
  payload: any;
}

interface GameState {
  events: GameEvent[];
  connectionStatus: ConnectionStatus;
  addEvent: (event: GameEvent) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  events: [],
  connectionStatus: "disconnected",
  
  addEvent: (event) => 
    set((state) => ({ 
      events: [...state.events, event] 
    })),
    
  setConnectionStatus: (status) => 
    set(() => ({ 
      connectionStatus: status 
    })),
    
  reset: () => 
    set(() => ({ 
      events: [], 
      connectionStatus: "disconnected" 
    })),
}));
