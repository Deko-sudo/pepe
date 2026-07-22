import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Dashboard } from "../src/pages/dashboard";

function renderWithRouter(ui: React.ReactNode) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("Dashboard", () => {
  it("renders Pepe title", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Pepe")).toBeInTheDocument();
  });

  it("renders Bitcoin 24h block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Bitcoin за 24 часа")).toBeInTheDocument();
    expect(screen.getByText("$118,420.50")).toBeInTheDocument();
  });

  it("renders market background block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Общий фон рынка")).toBeInTheDocument();
  });

  it("renders tracked assets block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Отслеживаемые активы")).toBeInTheDocument();
  });

  it("renders trading session block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Текущая торговая сессия")).toBeInTheDocument();
  });

  it("renders latest summary block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("Последняя сводка")).toBeInTheDocument();
  });

  it("renders AI Support Beta block", () => {
    renderWithRouter(<Dashboard />);
    expect(screen.getByText("AI Support")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("renders disclaimer", () => {
    renderWithRouter(<Dashboard />);
    expect(
      screen.getByText(/Демонстрационный интерфейс/)
    ).toBeInTheDocument();
  });

  it("marks mock data as demo", () => {
    renderWithRouter(<Dashboard />);
    const demoLabels = screen.getAllByText("Демонстрационные данные");
    expect(demoLabels.length).toBeGreaterThan(0);
  });
});
