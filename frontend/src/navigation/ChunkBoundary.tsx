import { Component, type ReactNode } from "react";
import { tText } from "../i18n/language";

export class ChunkBoundary extends Component<{ children: ReactNode; resetKey?: string; fallback?: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(previous: Readonly<typeof this.props>) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) this.setState({ failed: false });
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return this.props.fallback ?? <div role="alert" className="error-panel">
      <p>{tText("Unable to load this section. Reload the page to retry.")}</p>
      <button type="button" onClick={() => window.location.reload()}>{tText("Retry")}</button>
    </div>;
  }
}
