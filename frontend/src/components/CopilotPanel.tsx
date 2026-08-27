import { useState } from "react";
import { useI18n } from "../i18n/I18nContext";
import { api } from "../api/client";

interface CopilotTurn {
  question: string;
  answer: string | null;
  unavailable: boolean;
}

/** Zona "panel del copiloto" del layout de 3 zonas (Fase 17). El pipeline real
 * (retrieve_ai_context -> LLM -> citas) es la Fase 18 — bloqueada por falta de una API key de
 * proveedor LLM/embeddings. Esta UI ya está lista para consumir POST /copilot/ask en cuanto
 * exista; hasta entonces degrada con gracia en vez de romperse. */
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
      setTurns((prev) => [...prev, { question: asked, answer: result.answer, unavailable: false }]);
    } catch {
      setTurns((prev) => [...prev, { question: asked, answer: null, unavailable: true }]);
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
        />
        <button onClick={() => void ask()}>{t("copilot.send")}</button>
      </div>
    </aside>
  );
}
