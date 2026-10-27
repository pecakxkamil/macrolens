export type AppRoute =
  | { section: "overview"; view: "brief"; hash: string }
  | { section: "calendar"; view:"calendar"; hash:string }
  | { section: "explore"; view: "indicators" | "charts"; hash: string; seriesId?: string }
  | { section: "research"; view: "mci" | "macro-market" | "relationships"; hash: string };

const legacyRoutes: Record<string, string> = {
  "/state": "/", "/charts": "/explore/charts", "/indicators": "/explore/indicators",
  "/macro-index": "/research/mci", "/market-comparison": "/research/macro-market",
  "/relationships": "/research/relationships", "/overview/calendar": "/calendar",
};

export function resolveRoute(hash: string): AppRoute {
  let path = hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  if (path.startsWith("/indicators/")) path = `/explore${path}`;
  else path = legacyRoutes[path] ?? path;
  if (path === "/calendar") return { section: "calendar", view: "calendar", hash: "#/calendar" };
  if (path === "/explore/charts") return { section: "explore", view: "charts", hash: `#${path}` };
  if (path === "/explore" || path === "/explore/indicators" || path.startsWith("/explore/indicators/")) {
    let seriesId: string | undefined;
    try { seriesId = decodeURIComponent(path.slice("/explore/indicators/".length)) || undefined; }
    catch { seriesId = "Invalid series ID"; }
    return { section: "explore", view: "indicators", seriesId,
      hash: path === "/explore" ? "#/explore/indicators" : `#${path}` };
  }
  if (path === "/research/mci") return { section: "research", view: "mci", hash: "#/research/mci" };
  if (path === "/research/macro-market") return { section: "research", view: "macro-market", hash: `#${path}` };
  if (path === "/research" || path === "/research/relationships") return { section: "research", view: "relationships", hash: "#/research/relationships" };
  return { section: "overview", view: "brief", hash: "#/" };
}
