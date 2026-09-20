import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "./App";
import { type UsaEconomyNow } from "./api/macrolens";

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
    core_pce: {
      observation_date: "2026-08-01",
      feature_as_of_date: "2026-09-03",
      mom: 0.1,
      yoy: 2.9,
      annualized_3m: 2.0,
      momentum: "decelerating",
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
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => snapshot,
    }),
  );
}

afterEach(() => {
  cleanup();
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
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => snapshot,
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("heading", { name: "USA Economy Now" })).toBeInTheDocument();
  });

  test("important numeric formatting removes floating-point noise", async () => {
    mockFetchSuccess();

    render(<App />);

    expect(await screen.findByText("3.71%")).toBeInTheDocument();
    expect(screen.getByText("0.09 pp")).toBeInTheDocument();
    expect(screen.queryByText("0.0899999999999999")).not.toBeInTheDocument();
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
