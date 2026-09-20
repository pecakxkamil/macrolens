export function formatDate(value?: string): string {
  return value || "-";
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
