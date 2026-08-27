/** Reemplazo puramente visual de los "..." genéricos — no introduce estado nuevo, solo se
 * renderiza donde ya existía una condición de carga (loading / loadState === "loading"). */
export function LoadingDots() {
  return (
    <span className="loading-dots" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}
