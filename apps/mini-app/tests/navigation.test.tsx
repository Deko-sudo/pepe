import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { BottomNav } from "../src/features/navigation/bottom-nav";

function renderWithRouter(ui: React.ReactNode) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("BottomNav", () => {
  it("renders all navigation items", () => {
    renderWithRouter(<BottomNav />);
    expect(screen.getByText("Главная")).toBeInTheDocument();
    expect(screen.getByText("Рынки")).toBeInTheDocument();
    expect(screen.getByText("Сессия")).toBeInTheDocument();
    expect(screen.getByText("Сводки")).toBeInTheDocument();
    expect(screen.getByText("Настройки")).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(5);
  });
});
