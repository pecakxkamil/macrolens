import { tText, tLabel } from "../i18n/language";
import { useId, useState } from "react";
import type { KeyboardEvent } from "react";
import { metricMetadata, type MetricKey, type MetricMetadata } from "../metricMetadata";

type InfoTooltipProps = { metricKey: MetricKey; label?: never; description?: never; trigger?: never } | { metricKey?: never; label: string; description: string; trigger?: string };
export function InfoTooltip(props: InfoTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipId = useId();
  const metadata: MetricMetadata | undefined = props.metricKey ? metricMetadata[props.metricKey] : undefined;

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Escape") {
      setIsOpen(false);
      event.currentTarget.blur();
    }
  }

  return (
    <span className={`info-tooltip${isOpen ? " info-tooltip--open" : ""}`}>
      <button
        type="button"
        className="info-tooltip__trigger"
        aria-label={tLabel(props.label ?? `About ${metadata!.label}`)}
        aria-describedby={tooltipId}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        onKeyDown={handleKeyDown}
      >
        {props.trigger ?? "i"}</button>
      <span id={tooltipId} role="tooltip" className="info-tooltip__content">
        <span>{tText(props.description ?? metadata!.description)}</span>
        {metadata?.methodology ? <span>{tText(metadata?.methodology)}</span> : null}
      </span>
    </span>
  );
}
