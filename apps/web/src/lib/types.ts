export interface AgentState {
  name: string;
  is_eliminated: boolean;
  role?: string;
}

export interface GameEvent {
  event_type:
    | "INIT"
    | "GAME_START"
    | "GAME_OVER"
    | "GAME_ERROR"
    | "ROUND_STARTED"
    | "AGENT_SPOKE"
    | "AGENT_DELIBERATED"
    | "POLL_RESULT"
    | "VOTE_CAST"
    | "ELIMINATION_RESULT"
    | "LAST_WORDS"
    | "ROLE_REVEAL"
    | "SURVIVOR_REACTED"
    | "REACTION"
    | "ERROR";
  timestamp: string;
  payload: any;
}
