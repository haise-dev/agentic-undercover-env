// Frontend-Backend Type Sync for Agentic Undercover WS Events and Game State

export enum Role {
  VILLAGER = "villager",
  IMPOSTER = "imposter",
}

export enum AgentType {
  AI = "ai",
  HUMAN = "human",
}

export enum Phase {
  INIT = "init",
  SPEAKING = "speaking",
  DELIBERATION = "deliberation",
  POLLING = "polling",
  VOTING = "voting",
  REACTION = "reaction",
  ENDGAME = "endgame",
}

export enum PollVote {
  VOTE_NOW = "vote_now",
  SKIP = "skip",
}

export enum GameResult {
  VILLAGERS_WIN = "villagers_win",
  IMPOSTER_WINS = "imposter_wins",
}

export enum LLMProvider {
  OPENAI = "openai",
  GEMINI = "gemini",
  GROQ = "groq",
  DEEPSEEK = "deepseek",
}

export interface AgentLLMConfig {
  provider: LLMProvider;
  model_name: string;
  temperature?: number;
  max_tokens?: number | null;
}

export interface AgentConfig {
  agent_id: string;
  display_name: string;
  display_color: string;
  agent_type: AgentType;
  llm_config?: AgentLLMConfig | null;
}

export interface EpisodeConfig {
  episode_id: string;
  topic: string;
  secret_word: string;
  agents: AgentConfig[];
  max_rounds: number;
}

export interface AgentRoleAssignment {
  agent_id: string;
  role: Role;
  secret_word: string | null;
  topic: string;
}

export interface PublicMessage {
  agent_id: string;
  display_name: string;
  phase: Phase;
  round_number: number;
  deliberation_round: number | null;
  content: string;
  timestamp: string;
}

export interface SystemAnnouncement {
  phase: Phase;
  round_number: number;
  content: string;
  timestamp: string;
}

export interface PollRecord {
  agent_id: string;
  poll_vote: PollVote;
  inner_thought: string;
  round_number: number;
}

export interface VoteRecord {
  voter_agent_id: string;
  target_agent_id: string;
  inner_thought: string;
}

export interface EliminationResult {
  eliminated_agent_id: string;
  vote_tally: Record<string, number>;
  was_tiebreak: boolean;
  tiebreak_candidates?: string[] | null;
}

export interface GameState {
  episode_id: string;
  config: EpisodeConfig;
  role_assignments: Record<string, AgentRoleAssignment>;
  current_turn_order: string[];
  current_phase: Phase;
  current_round: number;
  current_deliberation_round: number;
  agent_alive: Record<string, boolean>;
  all_messages: PublicMessage[];
  all_announcements: SystemAnnouncement[];
  poll_history: Record<number, PollRecord[]>;
  vote_records: VoteRecord[];
  elimination_result: EliminationResult | null;
  result: GameResult | null;
  winning_agent_ids: string[] | null;
  started_at: string;
  ended_at: string | null;
}

// WS Event Payloads strictly synchronized with Backend emitters

export interface GameStartAgent {
  agent_id: string;
  display_name: string;
  display_color: string;
  agent_type: AgentType;
  role: Role;
  secret_word: string | null;
}

export interface GameStartPayload {
  episode_id: string;
  topic: string;
  agents: GameStartAgent[];
  turn_order: string[];
}

export interface RoundStartedPayload {
  episode_id: string;
  round_number: number;
  turn_order: string[];
}

export interface AgentSpokePayload {
  agent_id: string;
  display_name: string;
  public_statement: string;
  phase: Phase.SPEAKING;
  round_number: number;
  inner_thought?: string;
}

export interface AgentDeliberatedPayload {
  agent_id: string;
  display_name: string;
  public_statement: string;
  phase: Phase.DELIBERATION;
  round_number: number;
  deliberation_round: number;
  inner_thought?: string;
}

export interface PollResultPayload {
  vote_now_count: number;
  skip_count: number;
  forced: boolean;
}

export interface VoteCastPayload {
  voter_agent_id: string;
  target_agent_id: string;
  round_number: number;
  inner_thought?: string;
}

export interface EliminationResultPayload {
  eliminated_agent_id: string;
  vote_tally: Record<string, number>;
  was_tiebreak: boolean;
  tiebreak_candidates: string[] | null;
  round_number: number;
}

export interface LastWordsPayload {
  agent_id: string;
  statement: string;
  round_number: number;
}

export interface RoleRevealPayload {
  agent_id: string;
  role: string;
  round_number: number;
}

export interface SurvivorReactedPayload {
  agent_id: string;
  statement: string;
  round_number: number;
}

export interface GameOverPayload {
  result: string;
  winning_agent_ids: string[];
  eliminated_agent_id: string;
  villager_word: string;
  imposter_word: string;
}

export interface GameErrorPayload {
  error_type: "rate_limit" | "unknown";
  provider: string;
  details: string;
  error: string;
}

// Discriminated union of WebSocket events
export type WsEvent =
  | { event_type: "GAME_START"; payload: GameStartPayload; episode_id: string; timestamp: string }
  | { event_type: "ROUND_STARTED"; payload: RoundStartedPayload; episode_id: string; timestamp: string }
  | { event_type: "AGENT_SPOKE"; payload: AgentSpokePayload; episode_id: string; timestamp: string }
  | { event_type: "AGENT_DELIBERATED"; payload: AgentDeliberatedPayload; episode_id: string; timestamp: string }
  | { event_type: "POLLING_STARTED"; payload: { round_number: number }; episode_id: string; timestamp: string }
  | { event_type: "POLL_RESULT"; payload: PollResultPayload; episode_id: string; timestamp: string }
  | { event_type: "VOTING_STARTED"; payload: { round_number: number }; episode_id: string; timestamp: string }
  | { event_type: "VOTE_CAST"; payload: VoteCastPayload; episode_id: string; timestamp: string }
  | { event_type: "ELIMINATION_RESULT"; payload: EliminationResultPayload; episode_id: string; timestamp: string }
  | { event_type: "LAST_WORDS"; payload: LastWordsPayload; episode_id: string; timestamp: string }
  | { event_type: "ROLE_REVEAL"; payload: RoleRevealPayload; episode_id: string; timestamp: string }
  | { event_type: "SURVIVOR_REACTED"; payload: SurvivorReactedPayload; episode_id: string; timestamp: string }
  | { event_type: "GAME_OVER"; payload: GameOverPayload; episode_id: string; timestamp: string }
  | { event_type: "GAME_ERROR"; payload: GameErrorPayload; episode_id: string; timestamp: string };
