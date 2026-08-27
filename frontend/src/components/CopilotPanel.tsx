import { useState } from "react";
import { useI18n } from "../i18n/I18nContext";
import { api } from "../api/client";

interface CopilotTurn {
  question: string;
  answer: string | null;
  citationCount: number;
  unavailable: boolean;
}

/** Zona "panel del copiloto" del layout de 3 zonas (Fase 17). Pipeline real desde la Fase 18:
 * pregunta -> embedding local -> retrieve_ai_context() (RLS) -> DeepSeek -> respuesta + citas. */
export function CopilotPanel() {
  const { t } = useI18n();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<CopilotTurn[]>([]);
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!question.trim()) return;
    const asked = question.trim();
    setQuestion("");
    setLoading(true);
    try {
      const result = await api.askCopilot(asked);
      setTurns((prev) => [...prev, { question: asked, answer: result.answer, citationCount: result.citations.length, unavailable: false }]);
    } catch {
      setTurns((prev) => [...prev, { question: asked, answer: null, citationCount: 0, unavailable: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="copilot-panel">
      <h2>{t("copilot.title")}</h2>
      <div className="copilot-turns">
        {turns.length === 0 && <p className="state-message">{t("copilot.empty")}</p>}
        {turns.map((turn, index) => (
          <div key={index} className="copilot-turn">
            <p className="copilot-question">{turn.question}</p>
            <p className={"copilot-answer" + (turn.unavailable ? " unavailable" : "")}>
              {turn.unavailable ? t("copilot.unavailable") : turn.answer}
            </p>
            {!turn.unavailable && turn.citationCount > 0 && (
              <p className="copilot-citations">
                {t("copilot.sources")} {turn.citationCount}
              </p>
            )}
          </div>
        ))}
        {loading && <p className="state-message">{t("copilot.thinking")}</p>}
      </div>
      <div className="composer">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void ask()}
          placeholder={t("copilot.placeholder")}
          disabled={loading}
        />
        <button onClick={() => void ask()} disabled={loading}>
          {t("copilot.send")}
        </button>
      </div>
    </aside>
  );
}
