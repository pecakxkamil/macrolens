import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "../App";
import { resolveRoute } from "./routes";

const mappings = [
  ["#/state", "#/", "overview", "USA Economy Now"],
  ["#/charts", "#/explore/charts", "explore", "Historical Charts"],
  ["#/indicators", "#/explore/indicators", "explore", "Indicators"],
  ["#/indicators/UNRATE", "#/explore/indicators/UNRATE", "explore", "Indicators"],
  ["#/macro-index", "#/research/mci", "research", "Macro Conditions Index"],
  ["#/market-comparison", "#/research/macro-market", "research", "Macro-Market Analysis"],
  ["#/relationships", "#/research/relationships", "research", "Compare Data"],
  ["#/calendar", "#/calendar", "calendar", "Calendar"],
  ["#/overview/calendar", "#/calendar", "calendar", "Calendar"],
] as const;

afterEach(() => { cleanup(); window.location.hash = ""; vi.unstubAllGlobals(); });

test.each(mappings)("legacy %s resolves and renders its matching destination", async (oldHash, hash, section, heading) => {
  for (const suffix of ["", "/"]) expect(resolveRoute(oldHash + suffix)).toMatchObject({ hash, section });
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
  window.location.hash = oldHash; render(<App />);
  await screen.findByRole("heading", { name: heading }, { timeout: 5000 });
  await waitFor(() => expect(window.location.hash).toBe(hash));
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual(["Overview", "Calendar", "Explore Data", "Research"]);
  const active = section === "overview" ? "Overview" : section === "calendar" ? "Calendar" : section === "explore" ? "Explore Data" : "Research";
  expect(within(nav).getByRole("link", { name: active })).toHaveAttribute("aria-current", "page");
  expect(screen.queryByRole("heading", { name: "Macro State" })).not.toBeInTheDocument();
});

test("simple view switches and hash history keep the active main section in sync", async () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
  window.location.hash = "#/research"; render(<App />);
  await screen.findByRole("heading", { name: "Compare Data" });
  expect(resolveRoute("#/research")).toMatchObject({ hash: "#/research/relationships", view: "relationships" });
  expect(within(screen.getByRole("navigation", { name: "Research views" })).getAllByRole("link").map(link => link.textContent)).toEqual(["Compare Data", "MCI Index", "MCI vs Markets"]);
  fireEvent.click(screen.getByRole("link", { name: "MCI Index" }));
  await screen.findByRole("heading", { name: "Macro Conditions Index" });
  expect(screen.getByText(/50 is a reference value, not a validated boundary/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: "MCI vs Markets" }));
  await screen.findByRole("heading", { name: "Macro-Market Analysis" });
  expect(screen.getByRole("region", { name: "Research question" })).toHaveTextContent("Nasdaq and Bitcoin");
  fireEvent.click(screen.getByRole("link", { name: "Compare Data" }));
  await screen.findByRole("heading", { name: "Compare Data" });
  expect(screen.queryByText("Loading current index...")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("link", { name: "Explore Data" }));
  await screen.findByRole("heading", { name: "Indicators" });
  fireEvent.click(screen.getByRole("link", { name: "Curated charts" }));
  await screen.findByRole("heading", { name: "Historical Charts" });
  act(() => { window.location.hash = "#/research/mci"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  await screen.findByRole("heading", { name: "Macro Conditions Index" });
  expect(screen.getByRole("link", { name: "Research" })).toHaveAttribute("aria-current", "page");
});

test("calendar is a main tab and the old address remains compatible", async () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
  window.location.hash = "#/overview/calendar"; render(<App />);
  await screen.findByRole("heading", { name: "Calendar" });
  expect(screen.getByRole("link",{name:"Calendar"})).toHaveAttribute("aria-current","page");
  fireEvent.click(screen.getByRole("link", { name: "Overview" }));
  await screen.findByRole("heading", { name: "USA Economy Now" });
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
});

test("route parsing handles defaults, unknown routes and encoded or malformed series IDs", () => {
  expect(resolveRoute("#/explore")).toMatchObject({ hash: "#/explore/indicators", seriesId: undefined });
  expect(resolveRoute("#/indicators/%55NRATE")).toMatchObject({ seriesId: "UNRATE" });
  expect(resolveRoute("#/indicators/%ZZ")).toMatchObject({ seriesId: "Invalid series ID" });
  expect(resolveRoute("#/unrecognized")).toMatchObject({ hash: "#/", section: "overview" });
});
