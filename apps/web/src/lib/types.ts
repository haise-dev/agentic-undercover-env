import { WsEvent } from "../types/events";

export * from "../types/events";

export type GameEvent = WsEvent;

export interface AgentState {
  name: string;
  is_eliminated: boolean;
  role?: string;
}
