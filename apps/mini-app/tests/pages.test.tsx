import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Markets } from "../src/pages/markets";
import { Reports } from "../src/pages/reports";
import { Settings } from "../src/pages/settings";

function renderWithRouter(ui: React.ReactNode) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("Markets", () => {
  it("renders Markets page", () => {
    renderWithRouter(<Markets />);
    expect(screen.getByText("Рынки")).toBeInTheDocument();
  });
});

describe("Reports", () => {
  it("renders Reports page", () => {
    renderWithRouter(<Reports />);
    expect(screen.getByText("Сводки")).toBeInTheDocument();
  });
});

describe("Settings", () => {
  it("renders Settings page", () => {
    renderWithRouter(<Settings />);
    expect(screen.getByText("Настройки")).toBeInTheDocument();
  });
});
