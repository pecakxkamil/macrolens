import { afterEach, expect, test, vi } from "vitest";
import { fetchLeadLag, fetchMarketComparison, fetchMciHistory } from "./macrolens";
import { previousMonthEnd } from "../datePeriods";

function mockFetch() {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ observations: [], rows: [] }) });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
afterEach(() => { vi.unstubAllGlobals(); });

test("PIT monthly views request completed months so the existing history cache is usable", async () => {
  const fetch = mockFetch();
  await fetchMciHistory({ startDate: "2023-10-19" }, "point_in_time");
  await fetchMarketComparison({ assets: ["NASDAQCOM"], macroHistoryType: "point_in_time", mode: "indexed", startDate: "2021-10-19" });
  await fetchLeadLag({ asset: "CBBTCUSD", macroHistoryType: "point_in_time", rollingWindow: 36, startDate: "2021-10-19" });
  for (const [input] of fetch.mock.calls) expect(new URL(input).searchParams.get("end_date")).toBe(previousMonthEnd(new Date()));
  expect(new URL(fetch.mock.calls[0][0]).searchParams.get("start_date")).toBe("2023-10-19");
  expect(new URL(fetch.mock.calls[1][0]).searchParams.get("assets")).toBe("NASDAQCOM");
  expect(new URL(fetch.mock.calls[2][0]).searchParams.get("rolling_window")).toBe("36");
});

test("explicit PIT reporting end dates are preserved", async () => {
  const fetch = mockFetch(); const endDate = "2025-04-30";
  await fetchMciHistory({ endDate }, "point_in_time");
  await fetchMarketComparison({ endDate, assets: ["NASDAQCOM"], macroHistoryType: "point_in_time", mode: "actual" });
  await fetchLeadLag({ endDate, asset: "CBBTCUSD", macroHistoryType: "point_in_time", rollingWindow: 24 });
  for (const [input] of fetch.mock.calls) expect(new URL(input).searchParams.get("end_date")).toBe(endDate);
});

test("current-vintage requests keep their existing date parameters", async () => {
  const fetch = mockFetch();
  await fetchMciHistory({}, "current_vintage");
  await fetchMarketComparison({ assets: ["NASDAQCOM"], macroHistoryType: "current_vintage", mode: "indexed" });
  await fetchLeadLag({ asset: "NASDAQCOM", macroHistoryType: "current_vintage", rollingWindow: 24 });
  for (const [input] of fetch.mock.calls) expect(new URL(input).searchParams.has("end_date")).toBe(false);
});

test("completed-month boundaries follow Poland local dates, including year transitions", () => {
  expect(previousMonthEnd(new Date("2026-09-30T22:30:00Z"))).toBe("2026-09-30");
  expect(previousMonthEnd(new Date("2026-12-31T23:30:00Z"))).toBe("2026-12-31");
  expect(previousMonthEnd(new Date("2026-01-15T12:00:00Z"))).toBe("2025-12-31");
});
