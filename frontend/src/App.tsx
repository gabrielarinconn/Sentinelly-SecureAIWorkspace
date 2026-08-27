import { useState } from "react";
import { useAuth } from "./auth/AuthContext";
import { LoginScreen } from "./components/LoginScreen";
import { Sidebar } from "./components/Sidebar";
import { ChatPanel } from "./components/ChatPanel";
import { CopilotPanel } from "./components/CopilotPanel";

export function App() {
  const { status } = useAuth();
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);

  if (status === "loading") return <div className="app-loading">…</div>;
  if (status === "anonymous") return <LoginScreen />;

  return (
    <div className="app-layout">
      <Sidebar activeChannelId={activeChannelId} onSelectChannel={setActiveChannelId} />
      <ChatPanel channelId={activeChannelId} />
      <CopilotPanel />
    </div>
  );
}
