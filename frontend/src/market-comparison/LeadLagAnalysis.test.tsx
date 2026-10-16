import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { LeadLagAnalysis, ScatterDetails } from "./LeadLagAnalysis";
import type { LeadLagResponse } from "../api/macrolens";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LineChart: ({ children, data }: { children: ReactNode; data: unknown }) => <div data-testid="rolling" data-rows={JSON.stringify(data)}>{children}</div>,
  ScatterChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Line: ({ connectNulls }: { connectNulls: boolean }) => <span data-testid="rolling-line" data-connect={String(connectNulls)} />,
  Scatter: () => <span data-testid="scatter" />, Bar: () => null,
  XAxis: () => null, YAxis: () => null, Tooltip: () => null, ReferenceLine: () => null, CartesianGrid: () => null,
}));
function data(empty = false): LeadLagResponse {
  return {
    macro_history_type: "point_in_time", lag_convention: "Corr(delta_MCI_t, R_asset_(t+k))", rolling_window: 24,
    maximum_price_age_days: 7, anchor_count: 30,
    assets: [{ asset_id: "NASDAQCOM", name: "Nasdaq Composite", missing_price_dates: [],
      lags: Array.from({ length: 13 }, (_, i) => ({ lag: i - 6, correlation: empty ? null : 0.2, n: empty ? 0 : 29,
        first_anchor_date: empty ? null : "2020-01-31", last_anchor_date: empty ? null : "2022-06-30", missing_anchor_count: empty ? 30 : 1,
        pairs: empty ? [] : [{ anchor_date: "2020-01-31", return_date: "2020-04-30", mci_change: 2.5, asset_return: -3.2,
          asset_id: "NASDAQCOM", asset_name: "Nasdaq Composite", price_observation_date: "2020-04-30", previous_price_observation_date: "2020-03-31" }],
        rolling: [{ anchor_date: "2022-01-31", correlation: empty ? null : 0.1, valid_pairs: empty ? 23 : 24 }],
      })) }],
    coverage: { first_anchor_date: "2020-01-31", last_anchor_date: "2022-06-30", missing_mci_change_dates: ["2021-01-31"] },
    boundary_policy: "Only MCI anchor t is restricted to the reporting range. Returns at t+k may lie outside it.",
    rolling_policy: "All calendar-month pairs must be valid; otherwise correlation is null.",
    limitations: "Multiple testing and unstable correlations require caution. PIT availability is date-level, not intraday. Same-month correlation is not a prediction.",
  };
}
function mock(empty = false) {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => data(empty) });
  vi.stubGlobal("fetch", fetch); return fetch;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("defaults to Nasdaq lag zero and 24 months; inherits PIT and reporting range", async () => {
  const fetch = mock(); render(<LeadLagAnalysis macro="point_in_time" startDate="2020-01-01" />);
  await screen.findByText("Correlation across all 13 lags");
  const url = new URL(String(fetch.mock.calls[0][0]));
  expect(url.searchParams.get("assets")).toBe("NASDAQCOM");
  expect(url.searchParams.get("macro_history_type")).toBe("point_in_time");
  expect(url.searchParams.get("start_date")).toBe("2020-01-01");
  expect(url.searchParams.get("rolling_window")).toBe("24");
  expect(screen.getByLabelText("Lag (calendar months)")).toHaveValue("0");
  expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(14);
});

test("+3 and -3 expose the direction and select actual lag without another request", async () => {
  const fetch = mock(); render(<LeadLagAnalysis macro="point_in_time" />);
  await screen.findByText("Correlation across all 13 lags");
  fireEvent.change(screen.getByLabelText("Lag (calendar months)"), { target: { value: "3" } });
  expect(screen.getAllByText("+3: MCI precedes return").length).toBeGreaterThan(1);
  fireEvent.change(screen.getByLabelText("Lag (calendar months)"), { target: { value: "-3" } });
  expect(screen.getAllByText("-3: return precedes MCI").length).toBeGreaterThan(1);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByTestId("rolling-line")).toHaveAttribute("data-connect", "false");
});

test("asset, macro history and rolling selector update requests", async () => {
  const fetch = mock(); const { rerender } = render(<LeadLagAnalysis macro="point_in_time" />);
  await screen.findByText("Correlation across all 13 lags");
  fireEvent.change(screen.getByLabelText("Rolling window"), { target: { value: "36" } });
  await waitFor(() => expect(new URL(String(fetch.mock.calls[fetch.mock.calls.length - 1][0])).searchParams.get("rolling_window")).toBe("36"));
  fireEvent.change(screen.getByLabelText("Analysis asset"), { target: { value: "CBBTCUSD" } });
  await waitFor(() => expect(new URL(String(fetch.mock.calls[fetch.mock.calls.length - 1][0])).searchParams.get("assets")).toBe("CBBTCUSD"));
  rerender(<LeadLagAnalysis macro="current_vintage" startDate="2021-01-01" />);
  await waitFor(() => expect(new URL(String(fetch.mock.calls[fetch.mock.calls.length - 1][0])).searchParams.get("macro_history_type")).toBe("current_vintage"));
});

test("scatter tooltip exposes months, units, values and asset identity", () => {
  render(<ScatterDetails pair={data().assets[0].lags[0].pairs[0]} />);
  expect(screen.getByText("Nasdaq Composite (NASDAQCOM)")).toBeInTheDocument();
  expect(screen.getByText("MCI anchor month: 2020-01-31")).toBeInTheDocument();
  expect(screen.getByText("Asset return month: 2020-04-30")).toBeInTheDocument();
  expect(screen.getByText("Delta MCI: 2.50 index points")).toBeInTheDocument();
  expect(screen.getByText("Asset return: -3.20%")).toBeInTheDocument();
});

test("missing data shows null statistics and no invented rolling or scatter observations", async () => {
  mock(true); render(<LeadLagAnalysis macro="point_in_time" />);
  await screen.findByText("No valid paired observations for this lag and range.");
  expect(screen.getByText(/No complete rolling windows/)).toBeInTheDocument();
  expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
  expect(screen.queryByTestId("rolling")).not.toBeInTheDocument();
  expect(within(screen.getByRole("table")).getAllByText("Unavailable")).toHaveLength(13);
});

test("methodology explains calendar alignment, future returns, missing windows and statistical limits", async () => {
  mock(); render(<LeadLagAnalysis macro="point_in_time" />);
  await screen.findByText("Correlation across all 13 lags");
  expect(screen.getByText(/never sequential row shifting/)).toBeInTheDocument();
  expect(screen.getByText(/not an investable signal/)).toBeInTheDocument();
  expect(screen.getByText(/Multiple testing and unstable correlations/)).toBeInTheDocument();
  expect(screen.getByText(/none is selected as an optimal lag/)).toBeInTheDocument();
  expect(screen.queryByText(/buy signal|sell signal|optimal predictive lag/i)).not.toBeInTheDocument();
});

test("loading and error can be retried", async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: false }).mockResolvedValue({ ok: true, json: async () => data() });
  vi.stubGlobal("fetch", fetch); render(<LeadLagAnalysis macro="point_in_time" />);
  expect(screen.getByText("Loading lead/lag analysis...")).toBeInTheDocument();
  await screen.findByRole("alert"); fireEvent.click(screen.getByText("Retry analysis"));
  await screen.findByText("Correlation across all 13 lags");
});
