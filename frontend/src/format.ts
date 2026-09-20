export function formatDate(value?: string): string {
  return value || "-";
}

export function formatObservationDate(value?: string, frequency?: string): string {
  if (!value) {
    return "-";
  }

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return value;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const normalizedFrequency = frequency?.toLowerCase();

  if (normalizedFrequency === "quarterly") {
    return `Q${Math.floor((month - 1) / 3) + 1} ${year}`;
  }

  const date = new Date(Date.UTC(year, month - 1, day));
  if (normalizedFrequency === "monthly") {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatNumber(value?: number, fractionDigits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatPercent(value?: number): string {
  return `${formatNumber(value)}%`;
}

export function formatPercentagePoint(value?: number): string {
  return `${formatNumber(value)} pp`;
}

export function formatClassification(value?: string): string {
  if (!value) {
    return "-";
  }

  const normalized = value.trim().replace(/[_-]+/g, " ").replace(/\s+/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
}
