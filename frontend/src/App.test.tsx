import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "./App";
import { type UsaEconomyNow } from "./api/macrolens";
import { formatObservationDate } from "./format";

const snapshot: UsaEconomyNow = {
  as_of_date: "2026-09-04",
  component_as_of_dates: {
    labor: "2026-09-01",
    inflation: "2026-09-03",
    growth: "2026-08-30",
    consumer: "2026-09-02",
    housing: "2026-08-28",
    financial_conditions: "2026-09-04",
  },
  labor: {
    as_of_date: "2026-09-01",
    overall_momentum: "mixed",
    payrolls: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-01",
      monthly_change: 180,
      monthly_change_ma_3m: 220,
      monthly_change_ma_6m: 200,
      momentum: "improving",
    },
    unemployment: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-01",
      level: 4.1,
      change_3m: -0.1,
      momentum: "stable",
    },
    initial_claims: {
      observation_date: "2026-08-30",
      feature_as_of_date: "2026-09-01",
      moving_average_4w: 240000,
      moving_average_13w: 220000,
      momentum: "weakening",
    },
    continuing_claims: {
      observation_date: "2026-08-23",
      feature_as_of_date: "2026-09-01",
      moving_average_4w: 1850000,
      moving_average_13w: 1820000,
      momentum: "weakening",
    },
    job_openings: {
      observation_date: "2026-07-01",
      feature_as_of_date: "2026-09-01",
      level: 7400,
      change_3m: -100,
      yoy: -2,
      direction: "falling",
    },
    labor_force_participation: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-01",
      level: 62.5,
      change_3m: 0.1,
      moving_average_3m: 62.4,
      direction: "rising",
    },
    average_hourly_earnings: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-01",
      mom: 0.3,
      yoy: 4.1,
      annualized_3m: 3.8,
    },
  },
  inflation: {
    as_of_date: "2026-09-03",
    headline_cpi: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.2,
      yoy: 3.712958105,
      annualized_3m: 2.5,
      momentum: "decelerating",
    },
    core_cpi: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.3,
      yoy: 3.2,
      annualized_3m: 3.5,
      momentum: "accelerating",
    },
    headline_pce: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.2,
      yoy: 2.8,
      annualized_3m: 2.4,
      momentum: "decelerating",
    },
    core_pce: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.1,
      yoy: 2.9,
      annualized_3m: 2.0,
      momentum: "decelerating",
    },
    employment_cost_index: {
      observation_date: "2026-07-01",
      feature_as_of_date: "2026-09-03",
      qoq: 0.9,
      yoy: 3.8,
    },
    average_hourly_earnings: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.3,
      yoy: 4.1,
      annualized_3m: 3.8,
    },
  },
  growth: {
    as_of_date: "2026-08-30",
    real_gdp: {
      observation_date: "2026-07-01",
      feature_as_of_date: "2026-08-30",
      qoq_annualized: 3.0,
      yoy: 2.0,
      momentum: "accelerating",
    },
    cfnai: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-30",
      level: 0.2,
      moving_average_3m: -0.1,
      position: "below_trend",
    },
    industrial_production: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-30",
      mom: 0.3,
      yoy: 3.0,
      annualized_3m: 4.0,
      momentum: "accelerating",
    },
    capacity_utilization: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-30",
      level: 78,
      change_3m: -0.2,
      moving_average_3m: 77.5,
      direction: "falling",
    },
    durable_goods_orders: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-30",
      mom: 0.5,
      yoy: 2.6,
      moving_average_3m: 290000,
      latest_direction: "rising",
    },
  },
  consumer: {
    as_of_date: "2026-09-02",
    retail_sales: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-02",
      mom: 0.3,
      yoy: 5.2,
      annualized_3m: 4.0,
      momentum: "accelerating",
      series_type: "nominal",
    },
    real_consumption: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-02",
      mom: 0.2,
      yoy: 2.1,
      annualized_3m: 3.0,
      momentum: "stable",
    },
    real_disposable_income: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-02",
      mom: 0.2,
      yoy: 2.4,
      annualized_3m: 2.8,
      momentum: "accelerating",
    },
    saving_rate: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-02",
      level: 4.5,
      change_3m: 0.2,
      moving_average_3m: 4.3,
      direction: "rising",
    },
  },
  housing: {
    as_of_date: "2026-08-28",
    housing_starts: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-28",
      level: 1400,
      mom: 1,
      yoy: 5,
      moving_average_3m: 1380,
      direction: "rising",
    },
    building_permits: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-28",
      level: 1390,
      mom: -1,
      yoy: 3,
      moving_average_3m: 1370,
      direction: "falling",
    },
    new_home_sales: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-08-28",
      level: 650,
      mom: 0,
      yoy: 2,
      moving_average_3m: 640,
      direction: "stable",
    },
    mortgage_rate: {
      observation_date: "2026-08-28",
      feature_as_of_date: "2026-08-28",
      level: 6.5,
      change_4w: 0.0899999999999999,
      change_13w: 0.5,
      moving_average_4w: 6.35,
      direction: "rising",
    },
  },
  financial_conditions: {
    as_of_date: "2026-09-04",
    fed_funds_rate: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      level: 5.33,
    },
    treasury_2y: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      level: 4.0,
    },
    treasury_10y: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      level: 4.5,
    },
    real_yield_10y: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      level: 2.1,
    },
    yield_curve_2s10s: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      dgs2: 4.0,
      dgs10: 4.5,
      spread: 0.0899999999999999,
      shape: "positive",
    },
    nfci: {
      observation_date: "2026-09-04",
      feature_as_of_date: "2026-09-04",
      level: 0.12,
      change_4w: 0.1,
      moving_average_4w: 0.05,
      position: "looser_than_average",
      direction: "tightening",
    },
  },
};

function mockFetchSuccess() {
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    const url = String(input);
    let payload: unknown;
    if (url.endsWith("/api/v1/economy/us")) {
      payload = snapshot;
    } else if (url.includes("/series/CPIAUCSL/features/yoy/history")) {
      payload = {
            series_id: "CPIAUCSL",
            frequency: "monthly",
            history_type: "current_vintage",
            observations: [
              { observation_date: "2026-07-01", feature_as_of_date: "2026-09-03", value: 3.54 },
              { observation_date: "2026-08-01", feature_as_of_date: "2026-09-03", value: 3.71 },
            ],
          };
    } else {
      const seriesHistory: Record<string, { frequency: string; values: number[]; dates: string[] }> = {
        UNEMPLOY: { frequency: "monthly", values: [7100, 7200], dates: ["2026-07-01", "2026-08-01"] },
        PAYEMS: { frequency: "monthly", values: [158900, 159100], dates: ["2026-07-01", "2026-08-01"] },
        ICSA: { frequency: "weekly", values: [219000, 224000], dates: ["2026-08-23", "2026-08-30"] },
        CCSA: { frequency: "weekly", values: [1810000, 1830000], dates: ["2026-08-16", "2026-08-23"] },
      };
      const seriesId = Object.keys(seriesHistory).find((id) =>
        url.endsWith(`/api/v1/series/${id}/history`),
      );
      const series = seriesId ? seriesHistory[seriesId] : undefined;
      payload = series
        ? {
            series_id: seriesId,
            frequency: series.frequency,
            history_type: "current_vintage",
            observations: series.values.map((value, index) => ({
              observation_date: series.dates[index],
              value,
            })),
          }
        : { history_type: "current_vintage", observations: [] };
    }

    return Promise.resolve({
      ok: true,
      json: async () => payload,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe("MacroLens dashboard", () => {
  test("page renders MacroLens and USA Economy Now", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByText("MacroLens")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "USA Economy Now" })).toBeInTheDocument();
  });

  test("loading state renders", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(<App />);

    expect(screen.getByText("Loading USA Economy Now...")).toBeInTheDocument();
  });

  test("six domain headings render after successful API response", async () => {
    mockFetchSuccess();

    render(<App />);

    for (const heading of [
      "LABOR",
      "INFLATION",
      "GROWTH",
      "CONSUMER",
      "HOUSING",
      "FINANCIAL CONDITIONS",
    ]) {
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });

  test("snake_case classification values are displayed human-readably", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByText("Below trend")).toBeInTheDocument();
    expect(screen.getByText("Looser than average")).toBeInTheDocument();
    expect(screen.getAllByText("Accelerating").length).toBeGreaterThan(0);
    expect(screen.getByText("Positive")).toBeInTheDocument();
    expect(screen.queryByText("below_trend")).not.toBeInTheDocument();
    expect(screen.queryByText("looser_than_average")).not.toBeInTheDocument();
  });

  test("component freshness renders", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByText("Component Freshness")).toBeInTheDocument();
    const freshness = screen.getByRole("region", { name: "Component Freshness" });
    expect(within(freshness).getByText("Labor")).toBeInTheDocument();
    expect(within(freshness).getByText("2026-09-01")).toBeInTheDocument();
    expect(within(freshness).getByText("Financial Conditions")).toBeInTheDocument();
    expect(within(freshness).getByText("2026-09-04")).toBeInTheDocument();
  });

  test("API error state renders", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("MacroLens API is unavailable");
  });

  test("retry triggers another request", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((input: string | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/economy/us")) {
          const economyCalls = fetchMock.mock.calls.filter(([calledUrl]) =>
            String(calledUrl).endsWith("/api/v1/economy/us"),
          ).length;
          return economyCalls === 1
            ? Promise.reject(new Error("offline"))
            : Promise.resolve({ ok: true, json: async () => snapshot });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ history_type: "current_vintage", observations: [] }),
        });
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));

    await waitFor(() => {
      const economyCalls = fetchMock.mock.calls.filter(([url]) =>
        String(url).endsWith("/api/v1/economy/us"),
      );
      expect(economyCalls).toHaveLength(2);
    });
    expect(await screen.findByRole("heading", { name: "USA Economy Now" })).toBeInTheDocument();
  });

  test("important numeric formatting removes floating-point noise", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByText("3.71%")).toBeInTheDocument();
    expect(screen.getByText("0.09 pp")).toBeInTheDocument();
    expect(screen.queryByText("0.0899999999999999")).not.toBeInTheDocument();
  });

  test("current and previous values render from snapshot and history", async () => {
    mockFetchSuccess();

    render(<App />);

    const label = await screen.findByText("Headline CPI YoY");
    const metric = label.closest(".metric");
    expect(metric).not.toBeNull();
    expect(within(metric as HTMLElement).getByText("3.71%")).toBeInTheDocument();
    expect(metric).toHaveTextContent("Previous: 3.54%");
    expect(metric).toHaveTextContent("Jul 2026");
    expect(metric).not.toHaveTextContent("2026-07-01");
  });

  test("unavailable previous value renders fallback", async () => {
    mockFetchSuccess();

    render(<App />);

    const label = await screen.findByText("Core CPI YoY");
    expect(label.closest(".metric")).toHaveTextContent("Previous: —");
  });

  test("observation dates format by series frequency", () => {
    expect(formatObservationDate("2026-07-01", "monthly")).toBe("Jul 2026");
    expect(formatObservationDate("2026-04-01", "quarterly")).toBe("Q2 2026");
    expect(formatObservationDate("2026-09-11", "weekly")).toBe("Sep 11, 2026");
    expect(formatObservationDate("2026-09-11", "daily")).toBe("Sep 11, 2026");
  });

  test("each domain separates key readings from interpretation", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findAllByRole("heading", { name: "Key readings" })).toHaveLength(6);
    expect(
      screen.getAllByRole("heading", { name: "Interpretation / momentum" }),
    ).toHaveLength(6);
  });

  test("important economic readings and numeric momentum evidence render", async () => {
    mockFetchSuccess();

    render(<App />);

    for (const label of [
      "Headline CPI YoY",
      "Real GDP QoQ annualized",
      "Real Consumption YoY",
      "Housing Starts",
      "Effective Fed Funds Rate",
    ]) {
      expect(await screen.findByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText(/3M avg change: 220K/)).toBeInTheDocument();
    expect(screen.getByText(/4W avg: 240K/)).toBeInTheDocument();
    expect(screen.getAllByText(/3M ann.:/).length).toBeGreaterThan(0);
  });

  test("unemployment rate and unemployment level remain distinct", async () => {
    mockFetchSuccess();

    render(<App />);

    const rate = await screen.findByText("Unemployment Rate");
    const level = screen.getByText("Unemployment Level");
    expect(rate.closest(".metric")).toHaveTextContent("4.10%");
    expect(level.closest(".metric")).toHaveTextContent("7.2M");
    expect(level.closest(".metric")).toHaveTextContent("Previous: 7.1M");
  });

  test("count and SAAR levels use human-friendly K and M formatting", async () => {
    mockFetchSuccess();

    render(<App />);

    expect((await screen.findByText("Initial Jobless Claims")).closest(".metric")).toHaveTextContent("224K");
    expect(screen.getByText("Total Nonfarm Payrolls").closest(".metric")).toHaveTextContent("159.1M");
    expect(screen.getByText("Housing Starts").closest(".metric")).toHaveTextContent("1.40M SAAR");
  });

  test("evaluative and descriptive classifications use appropriately distinct tones", async () => {
    mockFetchSuccess();

    render(<App />);

    const improving = await screen.findByText("Improving");
    const weakening = screen.getByText("Weakening");
    const rising = screen.getAllByText("Rising")[0];
    const falling = screen.getAllByText("Falling")[0];

    expect(improving).toHaveClass("classification-pill--positive");
    expect(weakening).toHaveClass("classification-pill--negative");
    const accelerating = screen.getAllByText("Accelerating")[0];
    const decelerating = screen.getAllByText("Decelerating")[0];
    expect(rising).toHaveClass("classification-pill--rising");
    expect(falling).toHaveClass("classification-pill--falling");
    expect(rising).not.toHaveClass("classification-pill--positive", "classification-pill--negative");
    expect(falling).not.toHaveClass("classification-pill--positive", "classification-pill--negative");
    expect(accelerating).toHaveClass("classification-pill--accelerating");
    expect(decelerating).toHaveClass("classification-pill--decelerating");
    expect(accelerating).not.toHaveClass("classification-pill--positive");
    expect(decelerating).not.toHaveClass("classification-pill--negative");
  });

  test("default view mode is All data", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByRole("button", { name: "All data" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Employment Cost Index YoY")).toBeInTheDocument();
  });

  test("Key data hides non-core metrics and retains headline metrics", async () => {
    mockFetchSuccess();

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Key data" }));

    expect(screen.queryByText("Employment Cost Index YoY")).not.toBeInTheDocument();
    expect(screen.queryByText("Continuing Claims")).not.toBeInTheDocument();
    expect(screen.getByText("Unemployment Rate")).toBeInTheDocument();
    expect(screen.getByText("Headline CPI YoY")).toBeInTheDocument();
    expect(screen.getByText("Real GDP momentum")).toBeInTheDocument();
    expect(screen.getByText("2s10s spread")).toBeInTheDocument();
  });

  test("Custom mode shows grouped metric checkboxes", async () => {
    mockFetchSuccess();

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Custom" }));

    expect(screen.getByRole("group", { name: "Custom metric selection" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Labor" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Unemployment Rate" })).toBeChecked();
  });

  test("custom selections control visible card metrics", async () => {
    mockFetchSuccess();

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Custom" }));
    const checkbox = screen.getByRole("checkbox", { name: "Employment Cost Index YoY" });
    fireEvent.click(checkbox);

    const inflationCard = screen.getByRole("heading", { name: "INFLATION" }).closest(".domain-card");
    expect(checkbox).not.toBeChecked();
    expect(within(inflationCard as HTMLElement).queryByText("Employment Cost Index YoY")).not.toBeInTheDocument();
  });

  test("view mode persists through localStorage", async () => {
    mockFetchSuccess();

    const firstRender = render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Key data" }));
    expect(localStorage.getItem("macrolens.dashboard.viewMode")).toBe("key");
    firstRender.unmount();

    render(<App />);
    expect(await screen.findByRole("button", { name: "Key data" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("custom metric selections persist through localStorage", async () => {
    mockFetchSuccess();

    const firstRender = render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Custom" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Employment Cost Index YoY" }));
    firstRender.unmount();

    render(<App />);
    const checkbox = await screen.findByRole("checkbox", {
      name: "Employment Cost Index YoY",
    });
    expect(checkbox).not.toBeChecked();
    const inflationCard = screen.getByRole("heading", { name: "INFLATION" }).closest(".domain-card");
    expect(within(inflationCard as HTMLElement).queryByText("Employment Cost Index YoY")).not.toBeInTheDocument();
  });

  test("metric information is keyboard and click accessible", async () => {
    mockFetchSuccess();

    render(<App />);

    const trigger = await screen.findByRole("button", { name: "About Overall momentum" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByText(/At least two improving components means Improving/),
    ).toBeInTheDocument();
    trigger.focus();
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  test("2s10s tooltip is descriptive and makes no recession claim", async () => {
    mockFetchSuccess();

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "About 2s10s shape" }));
    const tooltipText = screen.getByText(/purely mathematical description/i).parentElement;
    expect(tooltipText).toHaveTextContent(/not a recession or trading signal/i);
    expect(tooltipText).not.toHaveTextContent(/predicts|signals a recession/i);
  });

  test("no overall macro score is displayed", async () => {
    mockFetchSuccess();

    render(<App />);

    await screen.findByRole("heading", { name: "USA Economy Now" });
    expect(screen.queryByText(/macro score/i)).not.toBeInTheDocument();
  });

  test("no trading signal is generated", async () => {
    mockFetchSuccess();

    render(<App />);

    await screen.findByRole("heading", { name: "USA Economy Now" });
    expect(screen.getByText("Current-state macro dashboard. No trading signals.")).toBeInTheDocument();
    expect(screen.queryByText(/trading signal:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/buy|sell|risk-on|risk-off/i)).not.toBeInTheDocument();
  });
});
