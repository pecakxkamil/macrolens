import { lazy, Suspense } from "react";
import { tLabel, tText } from "../i18n/language";
import type { AppRoute } from "./routes";

const MacroIndexPage = lazy(() => import("../macro-index/MacroIndexPage").then((module) => ({ default: module.MacroIndexPage })));
const MarketComparisonPage = lazy(() => import("../market-comparison/MarketComparisonPage").then((module) => ({ default: module.MarketComparisonPage })));
const RelationshipsPage = lazy(() => import("../relationships/RelationshipsPage").then((module) => ({ default: module.RelationshipsPage })));
const views = [
  ["relationships", "Compare Data"], ["mci", "MCI Index"], ["macro-market", "MCI vs Markets"],
] as const;

export function ResearchPage({ route }: { route: Extract<AppRoute, { section: "research" }> }) {
  return <>
    <nav className="section-switch" aria-label={tLabel("Research views")}>
      {views.map(([view, label]) => <a key={view} href={`#/research/${view}`} aria-current={route.view === view ? "page" : undefined}>{tText(label)}</a>)}
    </nav>
    <Suspense fallback={<p className="loading-panel">{tText("Loading research view...")}</p>}>
      {route.view === "mci" ? <MacroIndexPage embedded /> : route.view === "macro-market" ? <MarketComparisonPage embedded /> : <RelationshipsPage embedded />}
    </Suspense>
  </>;
}
