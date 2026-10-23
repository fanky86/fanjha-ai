import { useEffect, useRef, useState, useCallback } from "react";

export type WSState = "connecting" | "connected" | "reconnecting" | "disconnected";

export function useWebSocket(
  buildId: string | null,
  onEvent: (data: any) => void
): { state: WSState; send: (msg: string) => void } {
  const [state, setState] = useState<WSState>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!buildId) {
      setState("disconnected");
      return;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const url = `${protocol}://${host}/api/builds/${buildId}/stream`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      setState("disconnected");
      return;
    }
    wsRef.current = ws;
    setState(retryRef.current === 0 ? "connecting" : "reconnecting");

    ws.onopen = () => {
      retryRef.current = 0;
      setState("connected");
    };
    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.event === "ping") {
          ws.send("ping");
          return;
        }
        if (data.event === "pong") return;
        onEventRef.current(data);
      } catch {
        // ignore
      }
    };
    ws.onclose = () => {
      setState("disconnected");
      const delay = Math.min(30000, 1000 * Math.pow(2, retryRef.current));
      retryRef.current += 1;
      timerRef.current = window.setTimeout(connect, delay);
    };
    ws.onerror = () => ws.close();
  }, [buildId]);

  useEffect(() => {
    connect();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  return { state, send };
}
