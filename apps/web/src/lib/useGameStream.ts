import { useEffect, useRef, useCallback } from "react";
import { useGameStore } from "./store";
import { WS_BASE_URL } from "./constants";

const RECONNECT_INTERVAL_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useGameStream(episodeId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const { addEvent, setConnectionStatus, connectionStatus } = useGameStore();

  const connect = useCallback(() => {
    if (!episodeId) return;

    // Prevent duplicate connections
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setConnectionStatus("connecting");
    const wsUrl = `${WS_BASE_URL}/ws/episodes/${episodeId}/stream`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          addEvent(event);
        } catch (error) {
          console.error("Failed to parse websocket message:", error);
        }
      };

      ws.onclose = (event) => {
        // Normal closure
        if (event.code === 1000 || event.code === 1001) {
          setConnectionStatus("disconnected");
          return;
        }

        // Abnormal closure -> attempt reconnect
        setConnectionStatus("error");
        
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          const delay = RECONNECT_INTERVAL_MS * Math.pow(1.5, reconnectAttempts.current - 1); // exponential backoff
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        // onerror is usually followed by onclose, so we don't need heavy logic here
        setConnectionStatus("error");
      };
    } catch (error) {
      console.error("WebSocket connection error:", error);
      setConnectionStatus("error");
    }
  }, [episodeId, addEvent, setConnectionStatus]);

  useEffect(() => {
    // Only connect if we have an episode ID
    if (episodeId) {
      connect();
    }

    return () => {
      // Cleanup on unmount or episodeId change
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        // Use 1000 normal closure so it doesn't trigger auto-reconnect
        wsRef.current.close(1000, "Component unmounted");
        wsRef.current = null;
      }
    };
  }, [episodeId, connect]);

  const sendCommand = useCallback((cmd: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(cmd);
    } else {
      console.warn("Cannot send command, WebSocket is not open.");
    }
  }, []);

  return { sendCommand, connectionStatus };
}
