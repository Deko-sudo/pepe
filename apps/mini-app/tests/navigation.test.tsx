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

function activeLabels(): string[] {
  return screen
    .getAllByRole("link")
    .filter((link) => link.classList.contains("is-active"))
    .map((link) => link.textContent ?? "");
}

function ariaCurrentLabels(): string[] {
  return screen
    .getAllByRole("link")
    .filter((link) => link.getAttribute("aria-current") === "page")
    .map((link) => link.textContent ?? "");
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

  it("marks only Home active on / without a session hash", () => {
    renderWithRouter(<BottomNav />, "/");

    expect(activeLabels()).toEqual(["Главная"]);
    expect(ariaCurrentLabels()).toEqual(["Главная"]);
  });

  it("marks only Session active on /#session-card", () => {
    renderWithRouter(<BottomNav />, "/#session-card");

    expect(activeLabels()).toEqual(["Сессия"]);
    expect(ariaCurrentLabels()).toEqual(["Сессия"]);
  });

  it("never marks both Home and Session active at the same time", () => {
    // Each render is isolated; verify exactly one active tab per route.
    const { unmount: unmountHome } = renderWithRouter(<BottomNav />, "/");
    expect(activeLabels()).toHaveLength(1);
    unmountHome();

    const { unmount: unmountSession } = renderWithRouter(<BottomNav />, "/#session-card");
    expect(activeLabels()).toHaveLength(1);
    unmountSession();
  });

  it("keeps session navigation inside the SPA", () => {
    renderWithRouter(<BottomNav />, "/markets");

    fireEvent.click(screen.getByRole("link", { name: "Сессия" }));

    expect(screen.getByRole("status", { name: "Текущий маршрут" })).toHaveTextContent(
      "/#session-card",
    );
  });

  it("sets the correct pathname and hash after SPA session navigation", () => {
    renderWithRouter(<BottomNav />, "/markets");

    fireEvent.click(screen.getByRole("link", { name: "Сессия" }));

    expect(screen.getByRole("status", { name: "Текущий маршрут" })).toHaveTextContent(
      "/#session-card",
    );
    expect(activeLabels()).toEqual(["Сессия"]);
  });

  it("does not trigger a full page reload on session navigation", () => {
    // A full reload would unmount the MemoryRouter and lose the LocationProbe;
    // if the probe still shows the updated route, navigation stayed in the SPA.
    renderWithRouter(<BottomNav />, "/markets");

    fireEvent.click(screen.getByRole("link", { name: "Сессия" }));

    expect(screen.getByRole("status", { name: "Текущий маршрут" })).toHaveTextContent(
      "/#session-card",
    );
  });

  it("marks only Markets active on /markets", () => {
    renderWithRouter(<BottomNav />, "/markets");
    expect(activeLabels()).toEqual(["Рынки"]);
  });

  it("marks only Reports active on /reports", () => {
    renderWithRouter(<BottomNav />, "/reports");
    expect(activeLabels()).toEqual(["Сводки"]);
  });

  it("marks only Settings active on /settings", () => {
    renderWithRouter(<BottomNav />, "/settings");
    expect(activeLabels()).toEqual(["Настройки"]);
  });
});
