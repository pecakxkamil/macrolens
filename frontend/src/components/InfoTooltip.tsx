import { useId, useState } from "react";
import type { KeyboardEvent } from "react";
import { metricMetadata, type MetricKey, type MetricMetadata } from "../metricMetadata";

export function InfoTooltip({ metricKey }: { metricKey: MetricKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipId = useId();
  const metadata: MetricMetadata = metricMetadata[metricKey];

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
        aria-label={`About ${metadata.label}`}
        aria-describedby={tooltipId}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        onKeyDown={handleKeyDown}
      >
        i
      </button>
      <span id={tooltipId} role="tooltip" className="info-tooltip__content">
        <span>{metadata.description}</span>
        {metadata.methodology ? <span>{metadata.methodology}</span> : null}
      </span>
    </span>
  );
}
