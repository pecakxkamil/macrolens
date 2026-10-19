import polish from "./pl.json";
export type Language = "en" | "pl";
const STORAGE_KEY = "macrolens.language";
function savedLanguage(): Language {
  try { return localStorage.getItem(STORAGE_KEY) === "pl" ? "pl" : "en"; } catch { return "en"; }
}
let language: Language = savedLanguage();
const listeners = new Set<() => void>();
export const getLanguage = () => language;
export const getLocale = () => language === "pl" ? "pl-PL" : "en-US";
export const subscribeLanguage = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
export function setLanguage(next: Language) {
  language = next;
  try { localStorage.setItem(STORAGE_KEY, next); } catch { /* Translation also works without browser storage. */ }
  if (typeof document !== "undefined") document.documentElement.lang = next;
  listeners.forEach((listener) => listener());
}
if (typeof document !== "undefined") document.documentElement.lang = language;
if (typeof window !== "undefined") window.addEventListener("storage", (event) => {
  if (event.key === STORAGE_KEY) setLanguage(event.newValue === "pl" ? "pl" : "en");
});
const dictionary = polish as Record<string, string>;
const normalize = (text: string) => text.replace(/\s+/g, " ").trim();
const exact = new Map(Object.entries(dictionary).map(([key, value]) => [normalize(key).toLowerCase(), value]));
const outputs = new Set(Object.values(dictionary));
const cache = new Map<string, string>();
const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// One pass through approved phrases, longest first. Matches never run on their
// own translated output, and identifiers/URLs are protected from substitutions.
const keys = [...exact.keys()].filter((key) => key.length > 1).sort((a,b) => b.length - a.length);
const phrases = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${keys.map(escape).join("|")})(?![\\p{L}\\p{N}_])`, "giu");
function translated(text: string): string {
  if (outputs.has(text)) return text;
  const cached = cache.get(text);
  if (cached !== undefined) return cached;
  const match = exact.get(normalize(text).toLowerCase());
  if (match) return text.replace(text.trim(), match);
  // Preserve URLs, raw feature identifiers and source/feature tuples in reports.
  const protectedParts = /(https?:\/\/[^\s)]+|`[^`]*`|\[[a-z][a-z_0-9]*\]|\([A-Z0-9_]+, [a-z_]+\)|\b[a-z]+_[a-z_0-9]+\b)/g;
  const result = text.split(protectedParts).map((part, index) => index % 2 ? part :
    part.replace(phrases, (source) => exact.get(source.toLowerCase()) ?? source)).join("");
  const clean = result.replace(/proc\.\./g, "proc.");
  cache.set(text, clean);
  return clean;
}
export function t(text: string): string { return language === "pl" ? translated(text) : text; }
export function tText<T>(value: T): T {
  if (typeof value === "string") return t(value) as T;
  if (Array.isArray(value)) return value.map((item) => tText(item)) as T;
  return value;
}
export function tLabel<T>(value: T): T {
  if (typeof value === "string") return t(value) as T;
  if (value && typeof value === "object" && !("$$typeof" in value)) {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, ["value", "label", "name"].includes(key) ? tText(item) : item])) as T;
  }
  return value;
}
