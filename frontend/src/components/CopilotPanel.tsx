import { useEffect, useState } from "react";
import { useI18n } from "../i18n/I18nContext";
import { api } from "../api/client";
import type { Citation } from "../api/types";
import { LoadingDots } from "./LoadingDots";
import { Avatar } from "./Avatar";

interface CopilotTurn {
  question: string;
  answer: string | null;
  citations: Citation[];
  unavailable: boolean;
}

/** retrieve_ai_context() siempre trae hasta 5 candidatos por similitud vectorial, pero el LLM
 * solo termina usando (y citando con "[N]") los que de verdad responden la pregunta — el resto
 * son candidatos descartados, no fuentes reales. Sin este filtro, el panel mostraba las 5
 * tarjetas aunque la respuesta solo citara una. Si el LLM no citó ningún número (raro, rompe la
 * regla 4 del prompt), se muestran todas como fallback en vez de dejar la lista vacía. */
function citedCitations(answer: string | null, citations: Citation[]): Citation[] {
  if (!answer) return citations;
  const cited = new Set(Array.from(answer.matchAll(/\[(\d+)\]/g), (m) => Number(m[1])));
  if (cited.size === 0) return citations;
  return citations.filter((c) => cited.has(c.citation_number));
}

/** Zona "panel del copiloto" del layout de 3 zonas (Fase 17). Pipeline real desde la Fase 18:
 * pregunta -> embedding local -> retrieve_ai_context() (RLS) -> DeepSeek -> respuesta + citas. */
interface CopilotPanelProps {
  onClose: () => void;
  onNavigateToMessage: (channelId: string, messageId: string) => void;
}

export function CopilotPanel({ onClose, onNavigateToMessage }: CopilotPanelProps) {
  const { t } = useI18n();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<CopilotTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [senderNames, setSenderNames] = useState<Record<string, string>>({});

  // Mismo directorio que ChatPanel usa para el nombre sobre la burbuja — aquí resuelve
  // "Mensaje de {nombre}" en cada tarjeta de cita, sin pedir un dato nuevo.
  useEffect(() => {
    api
      .listUsers()
      .then((users) => setSenderNames(Object.fromEntries(users.map((u) => [u.id, u.full_name]))))
      .catch(() => {
        // el nombre simplemente no se muestra si el directorio falla — no es crítico
      });
  }, []);

  const ask = async () => {
    if (!question.trim()) return;
    const asked = question.trim();
    setQuestion("");
    setLoading(true);
    try {
      const result = await api.askCopilot(asked);
      setTurns((prev) => [...prev, { question: asked, answer: result.answer, citations: result.citations, unavailable: false }]);
    } catch {
      setTurns((prev) => [...prev, { question: asked, answer: null, citations: [], unavailable: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="copilot-panel">
      <div className="copilot-header">
        <div>
          <h2>{t("copilot.title")}</h2>
          <span className="copilot-subtitle">{t("copilot.subtitle")}</span>
        </div>
        <button className="copilot-close-button" onClick={onClose} aria-label={t("copilot.close")} title={t("copilot.close")}>
          ✕
        </button>
      </div>
      <div className="copilot-turns">
        {turns.length === 0 && <p className="state-message">{t("copilot.empty")}</p>}
        {turns.map((turn, index) => {
          const visibleCitations = citedCitations(turn.answer, turn.citations);
          return (
          <div key={index} className="copilot-turn">
            <p className="copilot-question">{turn.question}</p>
            <p className={"copilot-answer" + (turn.unavailable ? " unavailable" : "")}>
              {turn.unavailable ? t("copilot.unavailable") : turn.answer}
            </p>
            {!turn.unavailable && visibleCitations.length > 0 && (
              <div className="copilot-citation-list">
                <span className="copilot-citations-label">{t("copilot.sources")}</span>
                {visibleCitations.map((citation) => (
                  <button
                    key={citation.message_id}
                    className="copilot-citation-card"
                    onClick={() => onNavigateToMessage(citation.channel_id, citation.message_id)}
                  >
                    <Avatar seed={citation.sender_id} size="sm" />
                    <div className="copilot-citation-body">
                      <strong>
                        <span className="copilot-citation-number">[{citation.citation_number}]</span>{" "}
                        {t("copilot.messageFrom")} {senderNames[citation.sender_id] ?? ""}
                      </strong>
                      <span>{citation.content}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          );
        })}
        {loading && (
          <p className="state-message">
            <LoadingDots />
            {t("copilot.thinking")}
          </p>
        )}
      </div>
      <div className="composer">
        <input
          id="copilot-question-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void ask()}
          placeholder={t("copilot.placeholder")}
          disabled={loading}
          autoFocus
        />
        <button
          className="send-button"
          onClick={() => void ask()}
          disabled={loading}
          aria-label={t("copilot.send")}
          title={t("copilot.send")}
        >
          ➤
        </button>
      </div>
    </aside>
  );
}
