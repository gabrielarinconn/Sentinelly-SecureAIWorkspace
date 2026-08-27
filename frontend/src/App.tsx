import { useEffect, useState } from "react";
import { useAuth } from "./auth/AuthContext";
import { LoginScreen } from "./components/LoginScreen";
import { Sidebar } from "./components/Sidebar";
import { ChatPanel } from "./components/ChatPanel";
import { CopilotPanel } from "./components/CopilotPanel";
import { ProfileScreen } from "./components/ProfileScreen";
import { api } from "./api/client";
import type { Conversation } from "./api/types";

export function App() {
  const { status } = useAuth();
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);
  const [channels, setChannels] = useState<Conversation[] | "loading" | "error">("loading");
  const [copilotOpen, setCopilotOpen] = useState(true);
  const [profileOpen, setProfileOpen] = useState(false);
  const [jumpTarget, setJumpTarget] = useState<{ channelId: string; messageId: string } | null>(null);

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

  const onNavigateToMessage = (channelId: string, messageId: string) => {
    setActiveChannelId(channelId);
    setJumpTarget({ channelId, messageId });
  };

  if (status === "loading") return <div className="app-loading">…</div>;
  if (status === "anonymous") return <LoginScreen />;
  if (profileOpen) return <ProfileScreen onBack={() => setProfileOpen(false)} />;

  const activeChannel = Array.isArray(channels)
    ? (channels.find((c) => c.channel_id === activeChannelId) ?? null)
    : null;
  const jumpMessageId = jumpTarget && jumpTarget.channelId === activeChannelId ? jumpTarget.messageId : null;

  return (
    <div className={"app-layout" + (copilotOpen ? "" : " copilot-closed")}>
      <Sidebar
        channels={channels}
        activeChannelId={activeChannelId}
        onSelectChannel={setActiveChannelId}
        onDirectMessageStarted={onDirectMessageStarted}
        onOpenProfile={() => setProfileOpen(true)}
      />
      <ChatPanel
        channelId={activeChannelId}
        channel={activeChannel}
        onOpenCopilot={() => setCopilotOpen(true)}
        jumpMessageId={jumpMessageId}
        onJumpHandled={() => setJumpTarget(null)}
      />
      {copilotOpen && <CopilotPanel onClose={() => setCopilotOpen(false)} onNavigateToMessage={onNavigateToMessage} />}
    </div>
  );
}
