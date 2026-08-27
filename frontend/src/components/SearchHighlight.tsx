import { Fragment } from "react";

/** ts_headline() (Fase 8) devuelve texto con <mark>...</mark> alrededor de los términos
 * encontrados. El contenido del mensaje es dato NO confiable (R10) — nunca se usa
 * dangerouslySetInnerHTML acá. Se parsea el patrón fijo <mark>...</mark> y cada segmento se
 * renderiza como texto plano de React (auto-escapado), envolviendo solo lo resaltado en un
 * <mark> real. */
export function SearchHighlight({ headline }: { headline: string }) {
  const parts = headline.split(/(<mark>.*?<\/mark>)/g);
  return (
    <>
      {parts.map((part, index) => {
        const match = /^<mark>(.*)<\/mark>$/s.exec(part);
        return <Fragment key={index}>{match ? <mark>{match[1]}</mark> : part}</Fragment>;
      })}
    </>
  );
}
