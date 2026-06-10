// Vitest setup: extends expect with @testing-library/jest-dom matchers
// (toBeInTheDocument, etc.) and registers automatic DOM cleanup after each test.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
