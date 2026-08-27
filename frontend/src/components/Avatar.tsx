import { avatarFor } from "../lib/avatar";

interface AvatarProps {
  /** id o nombre ya existente (sender_id, channel_name) — nunca datos nuevos */
  seed?: string;
  /** para el usuario propio: su inicial, en vez de un emoji hasheado */
  initial?: string;
  size?: "sm" | "md";
}

export function Avatar({ seed, initial, size = "md" }: AvatarProps) {
  const sizeClass = size === "sm" ? "avatar-sm" : "avatar-md";
  if (initial) {
    return (
      <span className={`avatar ${sizeClass} avatar-initial`} aria-hidden="true">
        {initial}
      </span>
    );
  }
  const { emoji, colorClass } = avatarFor(seed ?? "");
  return (
    <span className={`avatar ${sizeClass} ${colorClass}`} aria-hidden="true">
      {emoji}
    </span>
  );
}
