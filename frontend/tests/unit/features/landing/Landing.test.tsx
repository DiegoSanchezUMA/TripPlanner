import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/(marketing)/page";
import { Landing } from "@/features/landing/Landing";

describe("Landing", () => {
  it("muestra el nombre de la aplicación como título principal", () => {
    render(<Landing />);

    expect(screen.getByRole("heading", { level: 1, name: "TripPlanner" })).toBeDefined();
  });

  it("es lo que muestra la página de inicio", () => {
    render(<HomePage />);

    expect(screen.getByRole("main")).toBeDefined();
  });
});
