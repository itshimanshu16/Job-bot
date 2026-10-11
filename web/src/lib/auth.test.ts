import { describe, expect, it } from "vitest";
import { clearAuthSession, isSessionAuthed, verifyPasscode } from "./auth";

describe("auth", () => {
  it("verifies valid passcodes and rejects invalid ones", () => {
    const mockStorage: Record<string, string> = {};
    const originalLocalStorage = globalThis.localStorage;
    (globalThis as unknown as { localStorage: Storage }).localStorage = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => { mockStorage[key] = val; },
      removeItem: (key: string) => { delete mockStorage[key]; },
      clear: () => {},
      key: () => null,
      length: 1,
    } as Storage;

    try {
      expect(isSessionAuthed()).toBe(false);
      expect(verifyPasscode("wrong-code")).toBe(false);
      expect(isSessionAuthed()).toBe(false);

      expect(verifyPasscode("himanshu2027")).toBe(true);
      expect(isSessionAuthed()).toBe(true);

      clearAuthSession();
      expect(isSessionAuthed()).toBe(false);

      expect(verifyPasscode("RADAR2027")).toBe(true); // case-insensitive
      expect(isSessionAuthed()).toBe(true);
    } finally {
      (globalThis as unknown as { localStorage: Storage | undefined }).localStorage = originalLocalStorage;
    }
  });
});
