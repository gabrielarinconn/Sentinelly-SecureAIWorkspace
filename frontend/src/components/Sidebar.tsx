import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nContext";
import { api } from "../api/client";
import type { Conversation } from "../api/types";

interface SidebarProps {
  activeChannelId: string | null;
  onSelectChannel: (channelId: string) => void;
}

/** Zona "perfil de usuario" (Fase 17, layout de 3 zonas) vive al pie de esta misma columna
 * junto con la zona de lista de canales — ver App.tsx para cómo se arma el layout completo. */
export function Sidebar({ activeChannelId, onSelectChannel }: SidebarProps) {
  const { user, logout } = useAuth();
  const { t, locale, setLocale } = useI18n();
  const [channels, setChannels] = useState<Conversation[] | "loading" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    setChannels("loading");
    api
      .listChannels()
      .then((result) => !cancelled && setChannels(result))
      .catch(() => !cancelled && setChannels("error"));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>{t("sidebar.channels")}</h2>
        <select value={locale} onChange={(e) => setLocale(e.target.value as "es" | "en")} aria-label="language">
          <option value="es">ES</option>
          <option value="en">EN</option>
        </select>
      </div>

      <nav className="channel-list">
        {channels === "loading" && <div className="state-message">…</div>}
        {channels === "error" && <div className="state-message error">{t("chat.errorLoading")}</div>}
        {Array.isArray(channels) &&
          channels.map((channel) => (
            <button
              key={channel.channel_id}
              className={"channel-item" + (channel.channel_id === activeChannelId ? " active" : "")}
              onClick={() => onSelectChannel(channel.channel_id)}
            >
              <span className="channel-name">#{channel.channel_name}</span>
              {channel.is_private && <span className="channel-badge">{t("sidebar.private")}</span>}
            </button>
          ))}
      </nav>

      <div className="user-profile">
        <div className="user-profile-info">
          <strong>{user?.full_name}</strong>
          <span>{user?.role_title}</span>
        </div>
        <button className="logout-button" onClick={() => void logout()}>
          {t("sidebar.logout")}
        </button>
      </div>
    </aside>
  );
}
