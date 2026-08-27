import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n/I18nContext";
import { api, ApiError } from "../api/client";
import { useChannelSocket } from "../hooks/useChannelSocket";
import type { Message, PendingMessage, SearchResult } from "../api/types";
import { SearchHighlight } from "./SearchHighlight";
import { LoadingDots } from "./LoadingDots";
import { Avatar } from "./Avatar";
import { avatarFor } from "../lib/avatar";
import type { Conversation } from "../api/types";
import { usePresence } from "../hooks/usePresence";

type LoadState = "loading" | "error" | "ready";

function upsert(list: PendingMessage[], incoming: Message, delivery: PendingMessage["delivery"], clientId?: string): PendingMessage[] {
  const key = clientId ?? incoming.id;
  const idx = list.findIndex((m) => m.clientId === key || m.id === incoming.id);
  const next: PendingMessage = { ...incoming, delivery, clientId: idx >= 0 ? list[idx].clientId : key };
  if (idx >= 0) {
    const copy = [...list];
    copy[idx] = next;
    return copy;
  }
  return [...list, next];
}

export function ChatPanel({ channelId, channel }: { channelId: string | null; channel: Conversation | null }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const onlineUserIds = usePresence();
  const [messages, setMessages] = useState<PendingMessage[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);

  const listRef = useRef<HTMLDivElement>(null);
  const previousScrollHeight = useRef(0);

  useEffect(() => {
    if (!channelId) return;
    setLoadState("loading");
    setMessages([]);
    setNextCursor(null);
    setSearchResults(null);
    api
      .getChannelMessages(channelId)
      .then((page) => {
        setMessages(page.items.slice().reverse().map((m) => ({ ...m, delivery: "sent" as const, clientId: m.id })));
        setNextCursor(page.next_cursor);
        setLoadState("ready");
        requestAnimationFrame(() => {
          if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
        });
      })
      .catch(() => setLoadState("error"));
  }, [channelId]);

  useChannelSocket(channelId, (event) => {
    if (event.event === "message_created") setMessages((prev) => upsert(prev, event, "sent"));
    if (event.event === "message_edited") setMessages((prev) => upsert(prev, event, "sent"));
    if (event.event === "message_deleted") setMessages((prev) => upsert(prev, event, "sent"));
  });

  const loadOlder = async () => {
    if (!channelId || !nextCursor || loadingOlder) return;
    setLoadingOlder(true);
    previousScrollHeight.current = listRef.current?.scrollHeight ?? 0;
    try {
      const page = await api.getChannelMessages(channelId, nextCursor);
      setMessages((prev) => [...page.items.slice().reverse().map((m) => ({ ...m, delivery: "sent" as const, clientId: m.id })), ...prev]);
      setNextCursor(page.next_cursor);
      requestAnimationFrame(() => {
        if (listRef.current) {
          listRef.current.scrollTop = listRef.current.scrollHeight - previousScrollHeight.current;
        }
      });
    } finally {
      setLoadingOlder(false);
    }
  };

  const send = async () => {
    if (!channelId || !draft.trim() || !user) return;
    const content = draft.trim();
    const clientId = crypto.randomUUID();
    setDraft("");
    setMessages((prev) => [
      ...prev,
      { id: clientId, channel_id: channelId, sender_id: user.id, content, status: "active", delivery: "pending", clientId },
    ]);
    requestAnimationFrame(() => {
      if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
    });
    try {
      const sent = await api.sendMessage(channelId, content);
      setMessages((prev) => upsert(prev, sent, "sent", clientId));
    } catch {
      setMessages((prev) => prev.map((m) => (m.clientId === clientId ? { ...m, delivery: "failed" } : m)));
    }
  };

  const retry = async (message: PendingMessage) => {
    if (!channelId || message.content === null) return;
    setMessages((prev) => prev.map((m) => (m.clientId === message.clientId ? { ...m, delivery: "pending" } : m)));
    try {
      const sent = await api.sendMessage(channelId, message.content);
      setMessages((prev) => upsert(prev, sent, "sent", message.clientId));
    } catch {
      setMessages((prev) => prev.map((m) => (m.clientId === message.clientId ? { ...m, delivery: "failed" } : m)));
    }
  };

  const startEdit = (message: PendingMessage) => {
    setEditingId(message.id);
    setEditDraft(message.content ?? "");
  };

  const saveEdit = async () => {
    if (!editingId || !editDraft.trim()) return;
    const updated = await api.editMessage(editingId, editDraft.trim());
    setMessages((prev) => upsert(prev, updated, "sent"));
    setEditingId(null);
  };

  const remove = async (message: PendingMessage) => {
    const updated = await api.deleteMessage(message.id);
    setMessages((prev) => upsert(prev, updated, "sent"));
  };

  const runSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    try {
      const page = await api.searchMessages(searchQuery.trim());
      setSearchResults(page.items);
    } catch (err) {
      setSearchResults([]);
      if (!(err instanceof ApiError)) throw err;
    }
  };

  if (!channelId) {
    return (
      <main className="chat-panel empty-state">
        <p>{t("chat.placeholder")}</p>
      </main>
    );
  }

  return (
    <main className="chat-panel">
      {channel && channel.is_direct ? (
        <div className="chat-header">
          <span className="avatar-status-wrap">
            <Avatar seed={channel.dm_peer_id ?? channel.channel_id} size="md" />
            <span
              className={"presence-dot" + (channel.dm_peer_id && onlineUserIds.has(channel.dm_peer_id) ? " online" : "")}
              aria-hidden="true"
            />
          </span>
          <div className="chat-header-info">
            <h2>{channel.dm_peer_name}</h2>
            <span className="chat-header-members">
              {channel.dm_peer_id && onlineUserIds.has(channel.dm_peer_id) ? t("sidebar.online") : t("sidebar.offline")}
            </span>
          </div>
        </div>
      ) : (
        channel && (
          <div className="chat-header">
            <span className="chat-header-icon" aria-hidden="true">
              {avatarFor(channel.channel_name ?? "").emoji}
            </span>
            <div className="chat-header-info">
              <h2>#{channel.channel_name}</h2>
              <span className="chat-header-members">
                {channel.member_count} {t("sidebar.members")}
              </span>
            </div>
            {channel.is_private && <span className="channel-badge">{t("sidebar.private")}</span>}
          </div>
        )
      )}
      <div className="chat-toolbar">
        <input
          className="search-input"
          placeholder={t("search.placeholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void runSearch()}
        />
        {searchResults !== null && (
          <button onClick={() => setSearchResults(null)}>{t("search.back")}</button>
        )}
      </div>

      {searchResults !== null ? (
        <div className="search-results">
          <h3>{t("search.results")}</h3>
          {searchResults.length === 0 && <div className="state-message">{t("search.noResults")}</div>}
          {searchResults.map((result) => (
            <div key={result.id} className="search-result">
              <SearchHighlight headline={result.headline} />
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="message-list" ref={listRef}>
            {loadState === "loading" && (
              <div className="state-message">
                <LoadingDots />
                {t("chat.loadingHistory")}
              </div>
            )}
            {loadState === "error" && <div className="state-message error">{t("chat.errorLoading")}</div>}
            {loadState === "ready" && messages.length === 0 && <div className="state-message">{t("chat.empty")}</div>}
            {loadState === "ready" && nextCursor && (
              <button className="load-older" onClick={() => void loadOlder()} disabled={loadingOlder}>
                {t("chat.loadOlder")}
              </button>
            )}
            {messages.map((message) => {
              const isOwn = message.sender_id === user?.id;
              return (
                <div key={message.clientId} className={"message" + (isOwn ? " own" : "")}>
                  {!isOwn && <Avatar seed={message.sender_id} size="sm" />}
                  <div className="message-content">
                    {editingId === message.id ? (
                      <div className="message-edit">
                        <input value={editDraft} onChange={(e) => setEditDraft(e.target.value)} autoFocus />
                        <button onClick={() => void saveEdit()}>{t("chat.send")}</button>
                      </div>
                    ) : (
                      <>
                        <div className={"message-bubble" + (message.status === "deleted" ? " deleted" : "")}>
                          {message.status === "deleted" ? (
                            <>
                              <span aria-hidden="true">🗑️</span> <em>{t("chat.deleted")}</em>
                            </>
                          ) : (
                            <>
                              {message.content}
                              {message.status === "edited" && <span className="edited-tag"> {t("chat.edited")}</span>}
                            </>
                          )}
                        </div>
                        {message.delivery === "pending" && (
                          <span className="delivery-tag">
                            <LoadingDots />
                            {t("chat.deliveryPending")}
                          </span>
                        )}
                        {message.delivery === "failed" && (
                          <span className="delivery-tag error">
                            {t("chat.deliveryFailed")}{" "}
                            <button onClick={() => void retry(message)}>{t("chat.retry")}</button>
                          </span>
                        )}
                        {isOwn && message.status !== "deleted" && message.delivery === "sent" && (
                          <div className="message-actions">
                            <button onClick={() => startEdit(message)}>{t("chat.edit")}</button>
                            <button onClick={() => void remove(message)}>{t("chat.delete")}</button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="composer">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void send()}
              placeholder={t("chat.composerPlaceholder")}
            />
            <button onClick={() => void send()}>{t("chat.send")}</button>
          </div>
        </>
      )}
    </main>
  );
}
