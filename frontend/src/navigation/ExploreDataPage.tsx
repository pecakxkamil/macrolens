import { lazy, Suspense } from "react";
import { tLabel, tText } from "../i18n/language";
import type { AppRoute } from "./routes";

const IndicatorsPage = lazy(() => import("../indicators/IndicatorsPage").then((module) => ({ default: module.IndicatorsPage })));
const ChartsPage = lazy(() => import("../charts/ChartsPage").then((module) => ({ default: module.ChartsPage })));

export function ExploreDataPage({ route }: { route: Extract<AppRoute, { section: "explore" }> }) {
  return <>
    <header className="section-header"><h1>{tText("Explore Data")}</h1><p>{tText("Inspect US macroeconomic indicators, their history, transformations and sources.")}</p></header>
    <nav className="section-switch" aria-label={tLabel("Explore Data views")}>
      <a href="#/explore/indicators" aria-current={route.view === "indicators" ? "page" : undefined}>{tText("Indicator explorer")}</a>
      <a href="#/explore/charts" aria-current={route.view === "charts" ? "page" : undefined}>{tText("Curated charts")}</a>
    </nav>
    <Suspense fallback={<p className="loading-panel">{tText("Loading data view...")}</p>}>
      {route.view === "charts" ? <ChartsPage embedded /> : <IndicatorsPage embedded seriesId={route.seriesId} />}
    </Suspense>
  </>;
}
