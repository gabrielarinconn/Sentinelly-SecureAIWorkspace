import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nContext";
import { useTheme } from "../theme/ThemeContext";
import { api } from "../api/client";
import type { Conversation, DirectoryUser } from "../api/types";
import { LoadingDots } from "./LoadingDots";
import { Avatar } from "./Avatar";
import { avatarFor } from "../lib/avatar";
import { usePresence } from "../hooks/usePresence";

interface SidebarProps {
  channels: Conversation[] | "loading" | "error";
  activeChannelId: string | null;
  onSelectChannel: (channelId: string) => void;
  onDirectMessageStarted: (conversation: Conversation) => void;
}

/** Zona "perfil de usuario" (Fase 17, layout de 3 zonas) vive al pie de esta misma columna
 * junto con la zona de lista de canales — ver App.tsx para cómo se arma el layout completo.
 * La lista de canales vive en App.tsx (fetch único, compartido con el header de ChatPanel). */
export function Sidebar({ channels, activeChannelId, onSelectChannel, onDirectMessageStarted }: SidebarProps) {
  const { user, logout } = useAuth();
  const { t, locale, setLocale } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [directory, setDirectory] = useState<DirectoryUser[] | "loading">("loading");
  const onlineUserIds = usePresence();

  useEffect(() => {
    if (!pickerOpen) return;
    let cancelled = false;
    setDirectory("loading");
    api
      .listUsers(search.trim() || undefined)
      .then((result) => !cancelled && setDirectory(result))
      .catch(() => !cancelled && setDirectory([]));
    return () => {
      cancelled = true;
    };
  }, [pickerOpen, search]);

  const startDm = async (otherUserId: string) => {
    const conversation = await api.startDirectMessage(otherUserId);
    onDirectMessageStarted(conversation);
    setPickerOpen(false);
    setSearch("");
  };

  const regularChannels = Array.isArray(channels) ? channels.filter((c) => !c.is_direct) : channels;
  const directMessages = Array.isArray(channels) ? channels.filter((c) => c.is_direct) : [];

  return (
    <aside className="sidebar">
      <div className="brand-row sidebar-brand">
        <span className="brand-mark" aria-hidden="true">
          🛡️
        </span>
        <strong>Sentinelly</strong>
      </div>

      <div className="sidebar-header">
        <h2>{t("sidebar.channels")}</h2>
        <div className="sidebar-controls">
          <select value={locale} onChange={(e) => setLocale(e.target.value as "es" | "en")} aria-label="language">
            <option value="es">ES</option>
            <option value="en">EN</option>
          </select>
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </div>

      <nav className="channel-list">
        {regularChannels === "loading" && (
          <div className="state-message">
            <LoadingDots />
          </div>
        )}
        {regularChannels === "error" && <div className="state-message error">{t("chat.errorLoading")}</div>}
        {Array.isArray(regularChannels) &&
          regularChannels.map((channel) => (
            <button
              key={channel.channel_id}
              className={"channel-item" + (channel.channel_id === activeChannelId ? " active" : "")}
              onClick={() => onSelectChannel(channel.channel_id)}
            >
              <span className="channel-name">
                <span aria-hidden="true">{avatarFor(channel.channel_name ?? "").emoji}</span> #{channel.channel_name}
              </span>
              {channel.is_private && <span className="channel-badge">{t("sidebar.private")}</span>}
              {channel.unread_count > 0 && <span className="unread-badge">{channel.unread_count}</span>}
            </button>
          ))}

        <div className="sidebar-section-header">
          <h3>{t("sidebar.directMessages")}</h3>
          <button
            className="dm-new-button"
            onClick={() => setPickerOpen((open) => !open)}
            aria-label={t("sidebar.newDm")}
            title={t("sidebar.newDm")}
          >
            +
          </button>
        </div>

        {pickerOpen && (
          <div className="dm-picker">
            <input
              className="dm-picker-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("sidebar.searchPeople")}
              autoFocus
            />
            {directory === "loading" && (
              <div className="state-message">
                <LoadingDots />
              </div>
            )}
            {Array.isArray(directory) && directory.length === 0 && (
              <div className="state-message">{t("search.noResults")}</div>
            )}
            {Array.isArray(directory) &&
              directory.map((person) => (
                <button key={person.id} className="dm-picker-result" onClick={() => void startDm(person.id)}>
                  <span className="avatar-status-wrap">
                    <Avatar initial={person.full_name.charAt(0)} size="sm" />
                    <span className={"presence-dot" + (onlineUserIds.has(person.id) ? " online" : "")} aria-hidden="true" />
                  </span>
                  <span className="dm-picker-result-info">
                    <strong>{person.full_name}</strong>
                    <span>{person.role_title}</span>
                  </span>
                </button>
              ))}
          </div>
        )}

        {directMessages.map((dm) => (
          <button
            key={dm.channel_id}
            className={"channel-item" + (dm.channel_id === activeChannelId ? " active" : "")}
            onClick={() => onSelectChannel(dm.channel_id)}
          >
            <span className="channel-name">
              <span className="avatar-status-wrap">
                <Avatar seed={dm.dm_peer_id ?? dm.channel_id} size="sm" />
                <span
                  className={"presence-dot" + (dm.dm_peer_id && onlineUserIds.has(dm.dm_peer_id) ? " online" : "")}
                  aria-hidden="true"
                />
              </span>
              {dm.dm_peer_name}
            </span>
            {dm.unread_count > 0 && <span className="unread-badge">{dm.unread_count}</span>}
          </button>
        ))}
      </nav>

      <div className="user-profile">
        <div className="user-profile-identity">
          <Avatar initial={user?.full_name?.charAt(0)} size="sm" />
          <div className="user-profile-info">
            <strong>{user?.full_name}</strong>
            <span>{user?.role_title}</span>
          </div>
        </div>
        <button className="logout-button" onClick={() => void logout()}>
          {t("sidebar.logout")}
        </button>
      </div>
    </aside>
  );
}
