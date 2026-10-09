import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "../App";
import type { MacroStateDomain, MacroStateResponse } from "../api/macrolens";

function domain(name: string, date: string, key: string, label: string, value: number, classification: string, evidence: string[]): MacroStateDomain {
  return {
    name, as_of_date: date, classifications: { overall_momentum: "improving" }, evidence,
    readings: [{ key, label, value, unit: "percent", observation_date: "2026-08-01", feature_as_of_date: date, classification }],
  };
}

const response: MacroStateResponse = {
  as_of_date: "2026-09-04",
  component_as_of_dates: {
    labor: "2026-09-01", inflation: "2026-09-03", growth: "2026-08-30",
    consumer: "2026-09-02", housing: "2026-08-28", financial_conditions: "2026-09-04",
  },
  domains: {
    labor: domain("Labor", "2026-09-01", "unemployment", "Unemployment rate", 4.1, "weakening",
      ["Labor overall momentum is improving.", "Unemployment momentum is weakening."]),
    inflation: domain("Inflation", "2026-09-03", "headline_cpi", "Headline CPI YoY", 3.2, "decelerating",
      ["Headline CPI momentum is decelerating.", "Core PCE momentum is stable."]),
    growth: domain("Growth", "2026-08-30", "real_gdp", "Real GDP QoQ annualized", 2.1, "decelerating",
      ["Real GDP momentum is decelerating.", "Industrial production momentum is accelerating."]),
    consumer: domain("Consumer", "2026-09-02", "retail_sales", "Retail sales YoY (nominal)", 3.5, "accelerating",
      ["Nominal retail sales momentum is accelerating.", "Saving rate is rising."]),
    housing: domain("Housing", "2026-08-28", "housing_starts", "Housing starts", 1400, "falling",
      ["Housing starts are falling.", "Building permits are rising."]),
    financial_conditions: domain("Financial Conditions", "2026-09-04", "nfci", "NFCI", -0.4, "looser_than_average",
      ["NFCI position is looser than average.", "NFCI direction is easing."]),
  },
  cross_currents: [{
    domain: "growth", summary: "Growth indicators are sending mixed directional signals.",
    evidence: [
      { label: "Real GDP momentum", classification: "decelerating" },
      { label: "Industrial production momentum", classification: "accelerating" },
    ],
  }],
};

function mockApi(data = response, failFirst = false) {
  let calls = 0;
  const fetchMock = vi.fn().mockImplementation((input: string | URL) => {
    if (!String(input).endsWith("/api/v1/economy/us/state")) return new Promise(() => undefined);
    calls += 1;
    return Promise.resolve({ ok: !(failFirst && calls === 1), json: async () => data });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
});

describe("Macro State v1", () => {
  test("navigation opens the state route and requests its endpoint", async () => {
    const fetchMock = mockApi();
    window.location.hash = "#/";
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Macro State" }));
    expect(await screen.findByRole("heading", { name: "Macro State" })).toBeInTheDocument();
    expect(await screen.findByText("As of: 2026-09-04")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Macro State" })).toHaveAttribute("aria-current", "page");
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/economy/us/state", expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  test("six domains, component freshness, readings and evidence render", async () => {
    mockApi();
    window.location.hash = "#/state";
    render(<App />);
    await screen.findByText("As of: 2026-09-04");
    const overview = screen.getByRole("region", { name: "Domain overview" });
    expect(within(overview).getAllByRole("article")).toHaveLength(6);
    for (const [key, item] of Object.entries(response.domains)) {
      const card = within(overview).getByRole("article", { name: `${item.name} state` });
      expect(within(card).getByRole("heading", { name: item.name })).toBeInTheDocument();
      expect(within(card).getByText(`As of ${item.as_of_date}`)).toBeInTheDocument();
      expect(within(card).getByText(item.readings[0].label)).toBeInTheDocument();
      for (const evidence of item.evidence) expect(within(card).getByText(evidence)).toBeInTheDocument();
      expect(within(screen.getByRole("region", { name: "Component freshness" })).getByText(`${item.name}: ${response.component_as_of_dates[key as keyof MacroStateResponse["domains"]]}`)).toBeInTheDocument();
    }
    expect(within(overview).getByText("4.10%")).toBeInTheDocument();
    expect(within(overview).getByText("Retail sales YoY (nominal)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View Labor indicators" })).toHaveAttribute("href", "#/indicators/PAYEMS");
    expect(screen.queryByText(/overall macro score|recession probability|trading signal|bullish|bearish/i)).not.toBeInTheDocument();
  });

  test("badges are positive or negative only for improving or weakening and tooltips reuse methodology", async () => {
    mockApi();
    window.location.hash = "#/state";
    render(<App />);
    await screen.findByText("As of: 2026-09-04");
    const labor = screen.getByRole("article", { name: "Labor state" });
    expect(within(labor).getByText("Improving")).toHaveClass("classification-pill--positive");
    expect(within(labor).getByText("Weakening")).toHaveClass("classification-pill--negative");
    const housing = screen.getByRole("article", { name: "Housing state" });
    expect(within(housing).getByText("Falling")).toHaveClass("classification-pill--context");
    const inflation = screen.getByRole("article", { name: "Inflation state" });
    expect(within(inflation).getByText("Decelerating")).toHaveClass("classification-pill--context");
    fireEvent.click(within(inflation).getByRole("button", { name: "About Headline CPI momentum" }));
    expect(within(inflation).getByRole("tooltip")).toHaveTextContent("Compares annualized 3-month inflation with YoY inflation");
  });

  test("cross-currents display explicit evidence and explanatory copy", async () => {
    mockApi();
    window.location.hash = "#/state";
    render(<App />);
    await screen.findByText("As of: 2026-09-04");
    const section = screen.getByRole("region", { name: "Cross-currents" });
    expect(within(section).getByText("Growth indicators are sending mixed directional signals.")).toBeInTheDocument();
    expect(within(section).getByText("Real GDP momentum")).toBeInTheDocument();
    expect(within(section).getByText("Industrial production momentum")).toBeInTheDocument();
    expect(within(section).getByText("Decelerating")).toBeInTheDocument();
    expect(within(section).getByText("Accelerating")).toBeInTheDocument();
    expect(within(section).getByText(/They are descriptive and are not forecasts/)).toBeInTheDocument();
  });

  test("empty cross-currents have a clean descriptive state", async () => {
    mockApi({ ...response, cross_currents: [] });
    window.location.hash = "#/state/";
    render(<App />);
    expect(await screen.findByText("No curated cross-currents match the current classifications.")).toBeInTheDocument();
  });

  test("error state can retry and recover", async () => {
    mockApi(response, true);
    window.location.hash = "#/state";
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Macro State is unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("As of: 2026-09-04")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
