import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { InfoTooltip } from "./InfoTooltip";
import { setLanguage } from "../i18n/language";
afterEach(() => { cleanup(); vi.useRealTimers(); setLanguage("en"); });
function note() {
  render(<InfoTooltip label="Explanation" description="A conditional economic note." bounded
    content={<span>Structured explanation</span>} />);
  return screen.getByRole("button", { name: "Explanation" });
}
test("focus alone does not open the note; activation opens it and Escape dismisses it", () => {
  const button = note();
  fireEvent.focus(button);
  expect(button).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("tooltip")).toHaveTextContent("Structured explanation");
  fireEvent.keyDown(button, { key: "Escape" });
  expect(button).toHaveAttribute("aria-expanded", "false");
});
test("a touch-style click keeps the note open until a second tap or outside press", () => {
  const button = note();
  fireEvent.focus(button);
  fireEvent.click(button);
  fireEvent.blur(button);
  fireEvent.pointerLeave(button);
  expect(button).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(button);
  fireEvent.pointerDown(document.body);
  expect(button).toHaveAttribute("aria-expanded", "false");
});

test("hovering arrows and interpretations cannot open or replace a popup", () => {
  render(<><InfoTooltip label="Arrow" description="Reading change" trigger={"\u2191"} closable />
    <InfoTooltip label="Interpretation" description="Domain interpretation" trigger="+" bounded /></>);
  const arrow = screen.getByRole("button", { name: "Arrow" });
  const interpretation = screen.getByRole("button", { name: "Interpretation" });
  for (const button of [arrow, interpretation]) {
    fireEvent.pointerEnter(button, { pointerType: "mouse" });
    fireEvent.mouseOver(button);
    fireEvent.focus(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
  }
  fireEvent.click(arrow);
  fireEvent.pointerEnter(interpretation, { pointerType: "mouse" });
  expect(arrow).toHaveAttribute("aria-expanded", "true");
  expect(interpretation).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(interpretation);
  expect(arrow).toHaveAttribute("aria-expanded", "false");
  expect(interpretation).toHaveAttribute("aria-expanded", "true");
  expect(screen.getAllByRole("button", { name: "Close explanation" })).toHaveLength(1);
  fireEvent.click(arrow);
  expect(arrow).toHaveAttribute("aria-expanded", "true");
  expect(interpretation).toHaveAttribute("aria-expanded", "false");
});

test.each(["en", "pl"] as const)("close button dismisses a pinned note and restores focus in %s", language => {
  setLanguage(language);
  const button = note();
  fireEvent.click(button);
  const close = screen.getByRole("button", { name: language === "pl" ? "Zamknij obja\u015bnienie" : "Close explanation" });
  close.focus();
  fireEvent.click(close);
  expect(button).toHaveAttribute("aria-expanded", "false");
  expect(button).toHaveFocus();
  expect(screen.queryByRole("button", { name: /Close explanation|Zamknij/ })).not.toBeInTheDocument();
});
test("Escape also dismisses the note while its close button has focus", () => {
  const button = note();
  fireEvent.click(button);
  const close = screen.getByRole("button", { name: "Close explanation" });
  close.focus();
  fireEvent.keyDown(close, { key: "Escape" });
  expect(button).toHaveAttribute("aria-expanded", "false");
  expect(button).toHaveFocus();
});

test.each(["en", "pl"] as const)("clicked arrow has a close button and can be reopened in %s", language => {
  setLanguage(language);
  render(<InfoTooltip label="Reading change" description="Lower than the previous month." trigger={"\u2193"} closable />);
  const arrow = screen.getByRole("button", { name: language === "pl" ? "Zmiana odczytu" : "Reading change" });
  const closeName = language === "pl" ? "Zamknij obja\u015bnienie" : "Close explanation";
  expect(screen.queryByRole("button", { name: closeName })).not.toBeInTheDocument();
  fireEvent.click(arrow);
  expect(arrow).toHaveAttribute("aria-expanded", "true");
  const close = screen.getByRole("button", { name: closeName });
  close.focus();
  fireEvent.click(close);
  expect(arrow).toHaveAttribute("aria-expanded", "false");
  expect(arrow).toHaveFocus();
  expect(screen.queryByRole("button", { name: closeName })).not.toBeInTheDocument();
  fireEvent.click(arrow);
  const reopenedClose = screen.getByRole("button", { name: closeName });
  reopenedClose.focus();
  fireEvent.keyDown(reopenedClose, { key: "Escape" });
  expect(arrow).toHaveAttribute("aria-expanded", "false");
  expect(arrow).toHaveFocus();
});
