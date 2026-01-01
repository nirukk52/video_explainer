/**
 * Tests for scene registry functions.
 *
 * Note: These tests mock the @project-scenes import since it's a webpack alias
 * that's only available at bundle time.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the @project-scenes module
vi.mock("@project-scenes", () => ({
  PROJECT_SCENES: {
    hook: () => null,
    phases: () => null,
    conclusion: () => null,
  },
  SceneComponent: {},
}));

// Import after mocking
import {
  getSceneByPath,
  getAllScenePaths,
  hasScene,
  getSceneTypes,
  PROJECT_SCENES,
} from "./index";

describe("Scene Registry", () => {
  describe("PROJECT_SCENES", () => {
    it("should export PROJECT_SCENES object", () => {
      expect(PROJECT_SCENES).toBeDefined();
      expect(typeof PROJECT_SCENES).toBe("object");
    });

    it("should have scene components", () => {
      expect(Object.keys(PROJECT_SCENES).length).toBeGreaterThan(0);
    });
  });

  describe("getSceneByPath", () => {
    it("should return scene component for valid project/type path", () => {
      const scene = getSceneByPath("llm-inference/hook");
      expect(scene).toBeDefined();
    });

    it("should return scene component for any project prefix", () => {
      // The function ignores the project prefix and looks up by type
      const scene = getSceneByPath("any-project/hook");
      expect(scene).toBeDefined();
    });

    it("should return undefined for non-existent scene type", () => {
      const scene = getSceneByPath("project/nonexistent");
      expect(scene).toBeUndefined();
    });

    it("should handle direct type lookup (fallback)", () => {
      const scene = getSceneByPath("hook");
      expect(scene).toBeDefined();
    });

    it("should return undefined for empty path", () => {
      const scene = getSceneByPath("");
      expect(scene).toBeUndefined();
    });
  });

  describe("getAllScenePaths", () => {
    it("should return array of scene paths", () => {
      const paths = getAllScenePaths();
      expect(Array.isArray(paths)).toBe(true);
      expect(paths.length).toBeGreaterThan(0);
    });

    it("should format paths as project/type", () => {
      const paths = getAllScenePaths();
      paths.forEach((path) => {
        expect(path).toMatch(/^project\/\w+$/);
      });
    });
  });

  describe("hasScene", () => {
    it("should return true for existing scene", () => {
      expect(hasScene("project/hook")).toBe(true);
    });

    it("should return false for non-existent scene", () => {
      expect(hasScene("project/nonexistent")).toBe(false);
    });
  });

  describe("getSceneTypes", () => {
    it("should return array of scene type names", () => {
      const types = getSceneTypes();
      expect(Array.isArray(types)).toBe(true);
      expect(types).toContain("hook");
      expect(types).toContain("phases");
      expect(types).toContain("conclusion");
    });
  });
});

describe("Scene Path Parsing", () => {
  it("should correctly split project/type format", () => {
    // Test the path parsing logic
    const path = "llm-inference/hook";
    const parts = path.split("/");
    expect(parts).toHaveLength(2);
    expect(parts[0]).toBe("llm-inference");
    expect(parts[1]).toBe("hook");
  });

  it("should handle paths without slash", () => {
    const path = "hook";
    const parts = path.split("/");
    expect(parts).toHaveLength(1);
  });

  it("should handle paths with multiple slashes", () => {
    const path = "project/sub/type";
    const parts = path.split("/");
    expect(parts).toHaveLength(3);
  });
});
