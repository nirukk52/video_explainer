/**
 * Main Scene Registry
 *
 * Imports scenes from the project directory via webpack alias.
 * The alias is configured at build time by render.mjs.
 *
 * Projects must export:
 * - PROJECT_SCENES: Record<string, SceneComponent> - scene registry
 * - SceneComponent: type for scene components
 */

import React from "react";

// Import project scenes via webpack alias (configured at build time in render.mjs)
// @ts-ignore - alias is configured dynamically at build time
import { PROJECT_SCENES, SceneComponent as ProjectSceneComponent } from "@project-scenes";

// Re-export types and scenes
export type SceneComponent = ProjectSceneComponent;
export { PROJECT_SCENES };

/**
 * Get a scene component by full path (e.g., "llm-inference/hook")
 *
 * @param scenePath - Full scene path in "project/type" format
 * @returns The scene component or undefined if not found
 */
export function getSceneByPath(scenePath: string): SceneComponent | undefined {
  const parts = scenePath.split("/");

  if (parts.length === 2) {
    const [project, type] = parts;
    // All scenes now come from the current project
    return PROJECT_SCENES[type];
  }

  // Fallback: try direct type lookup
  return PROJECT_SCENES[scenePath];
}

/**
 * Get all available scene paths
 */
export function getAllScenePaths(): string[] {
  return Object.keys(PROJECT_SCENES).map((type) => `project/${type}`);
}

/**
 * Check if a scene path exists
 */
export function hasScene(scenePath: string): boolean {
  return getSceneByPath(scenePath) !== undefined;
}

/**
 * Get all scene types
 */
export function getSceneTypes(): string[] {
  return Object.keys(PROJECT_SCENES);
}
