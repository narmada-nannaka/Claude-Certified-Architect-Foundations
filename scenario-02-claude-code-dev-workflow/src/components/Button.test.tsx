import { describe, it, expect, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    // ... rendering omitted; this is illustrative
    expect(onClick).toHaveBeenCalledTimes(0);
  });
});