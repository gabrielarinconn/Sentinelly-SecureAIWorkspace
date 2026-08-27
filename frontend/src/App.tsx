import { useEffect, useState } from "react";
import { useAuth } from "./auth/AuthContext";
import { LoginScreen } from "./components/LoginScreen";
import { Sidebar } from "./components/Sidebar";
import { ChatPanel } from "./components/ChatPanel";
import { CopilotPanel } from "./components/CopilotPanel";
import { api } from "./api/client";
import type { Conversation } from "./api/types";

export function App() {
  const { status } = useAuth();
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);
  const [channels, setChannels] = useState<Conversation[] | "loading" | "error">("loading");

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    setChannels("loading");
    api
      .listChannels()
      .then((result) => !cancelled && setChannels(result))
      .catch(() => !cancelled && setChannels("error"));
    return () => {
      cancelled = true;
    };
  }, [status]);

  useEffect(() => {
    if (!activeChannelId) return;
    api
      .markChannelRead(activeChannelId)
      .then(() => {
        setChannels((prev) =>
          Array.isArray(prev)
            ? prev.map((c) => (c.channel_id === activeChannelId ? { ...c, unread_count: 0 } : c))
            : prev,
        );
      })
      .catch(() => {
        // best-effort: si falla, el badge simplemente no baja hasta el próximo refresh
      });
  }, [activeChannelId]);

  const onDirectMessageStarted = (conversation: Conversation) => {
    setChannels((prev) => {
      if (!Array.isArray(prev)) return [conversation];
      const idx = prev.findIndex((c) => c.channel_id === conversation.channel_id);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = conversation;
        return copy;
      }
      return [conversation, ...prev];
    });
    setActiveChannelId(conversation.channel_id);
  };

  if (status === "loading") return <div className="app-loading">…</div>;
  if (status === "anonymous") return <LoginScreen />;

  const activeChannel = Array.isArray(channels)
    ? (channels.find((c) => c.channel_id === activeChannelId) ?? null)
    : null;

  return (
    <div className="app-layout">
      <Sidebar
        channels={channels}
        activeChannelId={activeChannelId}
        onSelectChannel={setActiveChannelId}
        onDirectMessageStarted={onDirectMessageStarted}
      />
      <ChatPanel channelId={activeChannelId} channel={activeChannel} />
      <CopilotPanel />
    </div>
  );
}
