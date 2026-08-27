import { useEffect, useState } from "react";
import { wsUrlForPresence } from "../api/client";

interface PresenceEvent {
  event: "presence_snapshot" | "presence_changed";
  user_ids?: string[];
  user_id?: string;
  online?: boolean;
}

/** Un único socket global (no uno por canal) — informa qué usuarios están online mientras la
 * sesión está abierta, sin importar qué canal esté activo (Sidebar necesita esto para la
 * lista de Mensajes Directos, no solo el canal que se está viendo). */
export function usePresence(): Set<string> {
  const [online, setOnline] = useState<Set<string>>(new Set());

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByEffect = false;

    const connect = () => {
      socket = new WebSocket(wsUrlForPresence());
      socket.onmessage = (raw) => {
        try {
          const event = JSON.parse(raw.data) as PresenceEvent;
          if (event.event === "presence_snapshot" && event.user_ids) {
            setOnline(new Set(event.user_ids));
          } else if (event.event === "presence_changed" && event.user_id) {
            setOnline((prev) => {
              const next = new Set(prev);
              if (event.online) next.add(event.user_id!);
              else next.delete(event.user_id!);
              return next;
            });
          }
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
  }, []);

  return online;
}
