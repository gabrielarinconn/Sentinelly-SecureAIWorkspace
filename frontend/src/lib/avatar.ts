const AVATAR_EMOJIS = ["🦊", "🌻", "🐢", "🍩", "🦄", "🌙", "🐙", "🚀", "🐝", "🌈"];
const AVATAR_COLOR_CLASSES = ["avatar-c0", "avatar-c1", "avatar-c2", "avatar-c3", "avatar-c4"];

/** Deriva un emoji + clase de color ESTABLES a partir de un id/nombre que ya tenemos (sender_id,
 * channel_name) — sin pedir ni inventar datos nuevos, solo una decoración determinística. */
export function avatarFor(seed: string): { emoji: string; colorClass: string } {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return {
    emoji: AVATAR_EMOJIS[hash % AVATAR_EMOJIS.length],
    colorClass: AVATAR_COLOR_CLASSES[hash % AVATAR_COLOR_CLASSES.length],
  };
}
