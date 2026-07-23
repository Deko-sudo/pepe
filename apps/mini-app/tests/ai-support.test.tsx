import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { Dashboard } from "../src/pages/dashboard";

function renderWithRouter(ui: React.ReactNode) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("AI Support Modal", () => {
  it("opens modal when AI Support button is clicked", () => {
    renderWithRouter(<Dashboard />);
    const aiButton = screen.getAllByText("AI Support")[0];
    fireEvent.click(aiButton);
    expect(
      screen.getByText("Ожидайте, функция находится в разработке.")
    ).toBeInTheDocument();
  });

  it("closes modal when Понятно is clicked", () => {
    renderWithRouter(<Dashboard />);
    const aiButton = screen.getAllByText("AI Support")[0];
    fireEvent.click(aiButton);
    fireEvent.click(screen.getByText("Понятно"));
    expect(
      screen.queryByText("Ожидайте, функция находится в разработке.")
    ).not.toBeInTheDocument();
  });
});
