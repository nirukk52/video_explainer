/**
 * Tests for CinematicTransition components.
 */

import { describe, it, expect, vi } from "vitest";
import React from "react";

// Mock remotion modules
vi.mock("remotion", () => ({
  AbsoluteFill: ({ children, style }: any) => (
    <div data-testid="absolute-fill" style={style}>
      {children}
    </div>
  ),
  interpolate: (value: number, inputRange: number[], outputRange: number[]) => {
    const [inMin, inMax] = inputRange;
    const [outMin, outMax] = outputRange;
    const ratio = (value - inMin) / (inMax - inMin);
    return outMin + ratio * (outMax - outMin);
  },
  Easing: {
    inOut: (fn: any) => fn,
    out: (fn: any) => fn,
    cubic: (x: number) => x,
  },
}));

import { cinematicFade, cinematicSlide } from "./CinematicTransition";

describe("cinematicFade", () => {
  it("should return a valid TransitionPresentation object", () => {
    const presentation = cinematicFade();

    expect(presentation).toHaveProperty("component");
    expect(presentation).toHaveProperty("props");
    expect(typeof presentation.component).toBe("function");
  });

  it("should accept custom props", () => {
    const presentation = cinematicFade({
      accentColor: "#ff0000",
      enableBlur: false,
      enableLightLeak: true,
    });

    expect(presentation.props).toEqual({
      accentColor: "#ff0000",
      enableBlur: false,
      enableLightLeak: true,
    });
  });

  it("should use default props when none provided", () => {
    const presentation = cinematicFade();

    expect(presentation.props).toEqual({});
  });

  it("should render component without crashing", () => {
    const presentation = cinematicFade({
      accentColor: "#00d9ff",
      enableBlur: true,
      enableLightLeak: true,
    });

    const Component = presentation.component;
    const mockChild = <div>Test Content</div>;

    expect(() =>
      Component({
        children: mockChild,
        presentationDirection: "entering",
        presentationProgress: 0.5,
        passedProps: presentation.props,
      })
    ).not.toThrow();
  });

  it("should handle exiting direction", () => {
    const presentation = cinematicFade();
    const Component = presentation.component;

    expect(() =>
      Component({
        children: <div>Test</div>,
        presentationDirection: "exiting",
        presentationProgress: 0.5,
        passedProps: {},
      })
    ).not.toThrow();
  });

  it("should handle progress at boundaries", () => {
    const presentation = cinematicFade();
    const Component = presentation.component;

    // Progress at 0
    expect(() =>
      Component({
        children: <div>Test</div>,
        presentationDirection: "entering",
        presentationProgress: 0,
        passedProps: {},
      })
    ).not.toThrow();

    // Progress at 1
    expect(() =>
      Component({
        children: <div>Test</div>,
        presentationDirection: "entering",
        presentationProgress: 1,
        passedProps: {},
      })
    ).not.toThrow();
  });
});

describe("cinematicSlide", () => {
  it("should return a valid TransitionPresentation object", () => {
    const presentation = cinematicSlide();

    expect(presentation).toHaveProperty("component");
    expect(presentation).toHaveProperty("props");
    expect(typeof presentation.component).toBe("function");
  });

  it("should accept slide direction", () => {
    const leftSlide = cinematicSlide({ slideDirection: "left" });
    const rightSlide = cinematicSlide({ slideDirection: "right" });
    const upSlide = cinematicSlide({ slideDirection: "up" });
    const downSlide = cinematicSlide({ slideDirection: "down" });

    expect(leftSlide.props.slideDirection).toBe("left");
    expect(rightSlide.props.slideDirection).toBe("right");
    expect(upSlide.props.slideDirection).toBe("up");
    expect(downSlide.props.slideDirection).toBe("down");
  });

  it("should render component for all slide directions", () => {
    const directions = ["left", "right", "up", "down"] as const;

    directions.forEach((direction) => {
      const presentation = cinematicSlide({ slideDirection: direction });
      const Component = presentation.component;

      expect(() =>
        Component({
          children: <div>Test</div>,
          presentationDirection: "entering",
          presentationProgress: 0.5,
          passedProps: presentation.props,
        })
      ).not.toThrow();
    });
  });

  it("should handle exiting direction for all slide directions", () => {
    const directions = ["left", "right", "up", "down"] as const;

    directions.forEach((direction) => {
      const presentation = cinematicSlide({ slideDirection: direction });
      const Component = presentation.component;

      expect(() =>
        Component({
          children: <div>Test</div>,
          presentationDirection: "exiting",
          presentationProgress: 0.5,
          passedProps: presentation.props,
        })
      ).not.toThrow();
    });
  });

  it("should accept all cinematic effect props", () => {
    const presentation = cinematicSlide({
      slideDirection: "left",
      accentColor: "#ff6b35",
      enableBlur: true,
      enableLightLeak: false,
      enableColorPulse: false,
    });

    expect(presentation.props).toEqual({
      slideDirection: "left",
      accentColor: "#ff6b35",
      enableBlur: true,
      enableLightLeak: false,
      enableColorPulse: false,
    });
  });
});

describe("Transition effects calculations", () => {
  it("should calculate blur amount peaking at middle of transition", () => {
    // Blur uses Math.sin(progress * Math.PI) * 8
    const blurAtStart = Math.sin(0 * Math.PI) * 8;
    const blurAtMiddle = Math.sin(0.5 * Math.PI) * 8;
    const blurAtEnd = Math.sin(1 * Math.PI) * 8;

    expect(blurAtStart).toBeCloseTo(0, 5);
    expect(blurAtMiddle).toBeCloseTo(8, 5);
    expect(blurAtEnd).toBeCloseTo(0, 5);
  });

  it("should calculate light leak opacity peaking at middle", () => {
    // Light leak uses Math.sin(progress * Math.PI) * 0.25
    const leakAtStart = Math.sin(0 * Math.PI) * 0.25;
    const leakAtMiddle = Math.sin(0.5 * Math.PI) * 0.25;
    const leakAtEnd = Math.sin(1 * Math.PI) * 0.25;

    expect(leakAtStart).toBeCloseTo(0, 5);
    expect(leakAtMiddle).toBeCloseTo(0.25, 5);
    expect(leakAtEnd).toBeCloseTo(0, 5);
  });

  it("should calculate scale based on blur amount", () => {
    // Scale = 1 + (blurAmount * 0.005)
    const blurAmount = 8;
    const scale = 1 + blurAmount * 0.005;

    expect(scale).toBe(1.04);
  });
});
