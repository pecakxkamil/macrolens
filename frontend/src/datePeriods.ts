import { getLanguage } from "./i18n/language";

export function warsawDate(instant: Date): string {
  const parts = new Intl.DateTimeFormat(getLanguage() === "pl" ? "pl-PL" : "en-GB", { timeZone: "Europe/Warsaw", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(instant);
  const get = (key: string) => parts.find((part) => part.type === key)!.value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}
export function previousMonthEnd(instant: Date): string {
  const [year, month] = warsawDate(instant).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, 0)).toISOString().slice(0, 10);
}
