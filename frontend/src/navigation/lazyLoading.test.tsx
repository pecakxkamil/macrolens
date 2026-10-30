import { lazy, Suspense } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { EconomyBriefResponse } from "../api/macrolens";
import App from "../App";
import { ChunkBoundary } from "./ChunkBoundary";
import { setLanguage, tText } from "../i18n/language";

const gate = vi.hoisted(() => {
  let release!: () => void;
  const promise = new Promise<void>(resolve => { release = resolve; });
  return { promise, release, imports: 0 };
});
vi.mock("../brief/EconomyBrief", async () => {
  gate.imports++;
  await gate.promise;
  return vi.importActual("../brief/EconomyBrief");
});

function brief(revision = "saved"): EconomyBriefResponse {
  const unavailable = { status: "unavailable" as const, data: null, error: "Synthetic absence" };
  return { data_revision: revision, automatic_refresh_supported: true,
    refresh: { status: "complete", publication_id: revision, next_check_at: new Date(Date.now() + 120_000).toISOString(), results: [] },
    assembled_at: new Date().toISOString(), timezone: "Europe/Warsaw", history_type: "current_vintage",
    snapshot: unavailable, state: unavailable, changes: unavailable, calendar: unavailable,
    calendar_start_date: "2026-10-26", calendar_end_date: "2026-11-02" };
}
async function navigate(hash: string) {
  await act(async () => { window.location.hash = hash; window.dispatchEvent(new HashChangeEvent("hashchange")); });
}
const settle = async () => { await act(async () => { for (let n = 0; n < 8; n++) await Promise.resolve(); }); };
beforeEach(() => { localStorage.clear(); setLanguage("en"); window.location.hash = "#/"; });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

test("cold Calendar does not import Overview; suspended rapid navigation never mounts an abandoned Overview or duplicates refresh", async () => {
  const api = vi.fn(async (input: string) => ({ ok: true, json: async () => input.includes("/calendar")
    ? { start_date: "2026-10-26", end_date: "2026-11-01", events: [], automatic_refresh_supported: false }
    : brief() }));
  vi.stubGlobal("fetch", api); window.location.hash = "#/calendar"; render(<App />);
  await screen.findByRole("heading", { name: "Calendar" }); expect(gate.imports).toBe(0);
  await navigate("#/"); expect(await screen.findByRole("status")).toHaveTextContent("Loading section...");
  expect(gate.imports).toBe(1);
  await navigate("#/calendar"); await screen.findByRole("heading", { name: "Calendar" });
  await act(async () => { gate.release(); await gate.promise; });
  expect(api.mock.calls.filter(([url]) => url.endsWith("/brief"))).toHaveLength(0);
  await navigate("#/"); await screen.findByRole("heading", { name: "Labor" });
  expect(document.querySelectorAll(".overview-domain")).toHaveLength(6);
  await navigate("#/calendar"); await screen.findByRole("heading", { name: "Calendar" });
  await navigate("#/"); await screen.findByRole("heading", { name: "Labor" });
  expect(api.mock.calls.filter(([url]) => url.endsWith("/brief"))).toHaveLength(2);
  expect(api.mock.calls.some(([url]) => url.includes("/refresh"))).toBe(false);
});

test("lazy Overview retains API error and Retry without re-importing the route", async () => {
  const api = vi.fn().mockRejectedValueOnce(new Error("Synthetic API failure"))
    .mockResolvedValue({ ok: true, json: async () => brief() });
  vi.stubGlobal("fetch", api); render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Economy Brief is unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Retry brief" }));
  await screen.findByRole("heading", { name: "Labor" }); expect(api).toHaveBeenCalledTimes(2);
  expect(gate.imports).toBe(1);
});

test("lazy Overview remount preserves the R3 deadline once, reloads the committed generation and cancels its timer on unmount", async () => {
  vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-30T12:00:00Z"));
  let reads = 0;
  const api = vi.fn(async (input: string, init?: RequestInit) => {
    if (input.includes("/calendar")) return { ok: true, json: async () => ({
      start_date: "2026-10-26", end_date: "2026-11-01", events: [], automatic_refresh_supported: false,
    }) };
    if (input.includes("/refresh")) {
      expect(init?.method).toBe("POST");
      return { ok: true, json: async () => ({ ...brief("published").refresh, refresh_mode: "bea_release_aware" }) };
    }
    reads++;
    const data = brief(reads <= 2 ? "saved" : "published");
    if (reads <= 2) data.refresh!.next_check_at = "2026-10-30T12:02:00Z";
    if (reads > 2) data.calendar = { status: "ready", error: null, data: {
      start_date: "2026-10-30", end_date: "2026-11-06", category: null,
      events: [{ release_id: 53, release_name: "Gross Domestic Product", release_date: "2026-10-31",
        release_time: "08:30:00", source_timezone: "America/New_York", release_datetime_utc: "2026-10-31T12:30:00Z",
        importance: "high", source_link: null, date_precision: "date", series: [] }] } };
    return { ok: true, json: async () => data };
  });
  vi.stubGlobal("fetch", api); const view = render(<App />); await settle();
  expect(document.querySelectorAll(".overview-domain")).toHaveLength(6);
  await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
  await navigate("#/calendar"); await settle();
  expect(screen.getByRole("heading", { name: "Calendar" })).toBeInTheDocument();
  await navigate("#/"); await settle();
  expect(reads).toBe(2);
  await act(async () => { await vi.advanceTimersByTimeAsync(60_000); }); await settle();
  expect(reads).toBe(3); expect(api.mock.calls.filter(([url]) => url.includes("/refresh"))).toHaveLength(1);
  expect(screen.getByText("Gross Domestic Product")).toBeInTheDocument();
  view.unmount(); await act(async () => { await vi.advanceTimersByTimeAsync(900_000); });
  expect(api).toHaveBeenCalledTimes(5);
});

test.each(["en", "pl"] as const)("chunk rejection has an accessible error and recovers on navigation in %s", async language => {
  setLanguage(language);
  const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
  const Broken = lazy(() => Promise.reject(new Error("Synthetic chunk failure")));
  const view = render(<ChunkBoundary resetKey="broken"><Suspense fallback={<p role="status">Loading</p>}><Broken /></Suspense></ChunkBoundary>);
  expect(await screen.findByRole("alert")).toHaveTextContent(tText("Unable to load this section. Reload the page to retry."));
  expect(screen.getByRole("button", { name: tText("Retry") })).toBeInTheDocument();
  expect(error.mock.calls.some(call => call.some(value => String(value).includes("Synthetic chunk failure")))).toBe(true);
  view.rerender(<ChunkBoundary resetKey="recovered"><p>Recovered route</p></ChunkBoundary>);
  expect(await screen.findByText("Recovered route")).toBeInTheDocument();
});
