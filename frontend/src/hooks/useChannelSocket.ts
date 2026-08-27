import { useEffect, useRef } from "react";
import { wsUrlForChannel } from "../api/client";
import type { Message } from "../api/types";

interface RealtimeEvent extends Message {
  event: "message_created" | "message_edited" | "message_deleted";
}

/** Fase 7: se conecta al canal activo y aplica cada evento a medida que llega — nunca antes
 * de que el servidor confirme el COMMIT, eso ya lo garantiza el backend. Reconecta con
 * backoff simple si la conexión se cae (Fase 7 P1: reconexión). */
export function useChannelSocket(channelId: string | null, onEvent: (event: RealtimeEvent) => void) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!channelId) return;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByEffect = false;

    const connect = () => {
      socket = new WebSocket(wsUrlForChannel(channelId));
      socket.onmessage = (raw) => {
        try {
          onEventRef.current(JSON.parse(raw.data) as RealtimeEvent);
        } catch {
          // evento malformado — se ignora, no debe tumbar la UI
        }
      };
      socket.onclose = () => {
        if (!closedByEffect) reconnectTimer = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closedByEffect = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [channelId]);
}
