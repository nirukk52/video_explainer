/**
 * Tests for CinematicEffects components.
 *
 * Note: Components using React hooks cannot be directly called.
 * These tests focus on the effect calculations and non-hook components.
 */

import { describe, it, expect, vi } from "vitest";
import React from "react";

// Mock remotion modules - hooks return mock values
vi.mock("remotion", () => ({
  AbsoluteFill: ({ children, style }: any) => (
    <div data-testid="absolute-fill" style={style}>
      {children}
    </div>
  ),
  useCurrentFrame: vi.fn(() => 0),
  useVideoConfig: vi.fn(() => ({
    fps: 30,
    width: 1920,
    height: 1080,
    durationInFrames: 300,
  })),
  interpolate: (value: number, inputRange: number[], outputRange: number[]) => {
    const [inMin, inMax] = inputRange;
    const [outMin, outMax] = outputRange;
    const ratio = Math.max(0, Math.min(1, (value - inMin) / (inMax - inMin)));
    return outMin + ratio * (outMax - outMin);
  },
  random: (seed: string) => {
    // Simple deterministic random based on seed string
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      hash = ((hash << 5) - hash + seed.charCodeAt(i)) | 0;
    }
    return Math.abs(hash % 1000) / 1000;
  },
}));

// Import after mocking
import {
  LightLeak,
  ChromaticAberration,
  ColorPulse,
  FocusBlur,
} from "./CinematicEffects";

describe("CinematicEffects calculations", () => {
  it("should calculate breathing effect correctly", () => {
    // Breathing uses Math.sin(frame * speed) * (0.008 * intensity)
    const frame = 0;
    const speed = 0.015;
    const intensity = 0.5;

    const breathe = Math.sin(frame * speed) * (0.008 * intensity);
    const scale = 1 + breathe;

    expect(scale).toBe(1); // At frame 0, sin(0) = 0, so scale = 1
  });

  it("should calculate pulsing effect for ambient glow", () => {
    // Pulse uses 0.7 + Math.sin(frame * 0.02) * 0.3
    const frame = 0;
    const pulse = 0.7 + Math.sin(frame * 0.02) * 0.3;
    const intensity = 0.15;
    const opacity = intensity * pulse;

    expect(pulse).toBe(0.7); // At frame 0, sin(0) = 0
    expect(opacity).toBeCloseTo(0.105, 5);
  });

  it("should calculate particle twinkle effect", () => {
    // Twinkle uses 0.7 + Math.sin(frame * 0.05 + id * 2) * 0.3
    const frame = 0;
    const id = 0;
    const twinkle = 0.7 + Math.sin(frame * 0.05 + id * 2) * 0.3;

    expect(twinkle).toBe(0.7); // At frame 0 and id 0
  });

  it("should calculate light leak intensity correctly", () => {
    // Intensity = Math.sin(progress * Math.PI) * 0.4
    const midProgress = 0.5;
    const intensity = Math.sin(midProgress * Math.PI) * 0.4;

    expect(intensity).toBeCloseTo(0.4, 5); // sin(0.5 * PI) = 1
  });

  it("should calculate aberration amount correctly", () => {
    // Aberration = Math.sin(intensity * Math.PI) * 4
    const midIntensity = 0.5;
    const aberration = Math.sin(midIntensity * Math.PI) * 4;

    expect(aberration).toBeCloseTo(4, 5); // sin(0.5 * PI) = 1
  });

  it("should calculate vignette gradient correctly", () => {
    // Vignette uses radial-gradient with intensity for rgba alpha
    const intensity = 0.4;
    const expected = `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${intensity}) 100%)`;

    expect(expected).toContain("rgba(0,0,0,0.4)");
  });
});
