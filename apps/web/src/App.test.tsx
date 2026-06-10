import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the VeriDoc AI heading (Wave 0 smoke test)", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /veridoc ai/i }),
    ).toBeInTheDocument();
  });
});
