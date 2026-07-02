export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Derives WS_BASE_URL from API_BASE_URL
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");
