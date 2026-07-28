import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { BottomNav } from "../src/features/navigation/bottom-nav";

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="Текущий маршрут">{location.pathname}{location.hash}</output>;
}

function renderWithRouter(ui: React.ReactNode, initialEntry = "/") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      {ui}
      <LocationProbe />
    </MemoryRouter>,
  );
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
    expect(screen.getByRole("link", { name: "Сессия" })).toHaveAttribute("href", "/#session-card");
  });

  it("keeps session navigation inside the SPA", () => {
    renderWithRouter(<BottomNav />, "/markets");

    fireEvent.click(screen.getByRole("link", { name: "Сессия" }));

    expect(screen.getByRole("status", { name: "Текущий маршрут" })).toHaveTextContent(
      "/#session-card",
    );
  });
});
