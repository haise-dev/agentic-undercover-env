export interface AgentState {
  name: string;
  is_eliminated: boolean;
  role?: string;
}

export interface GameEvent {
  event_type: "INIT" | "AGENT_SPOKE" | "VOTE_CAST" | "ELIMINATION_RESULT" | "ROLE_REVEAL" | "GAME_OVER" | "REACTION" | "ERROR";
  timestamp: string;
  payload: any;
}
