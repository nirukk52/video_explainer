/**
 * CinematicTransition - Custom transition presentation for Remotion
 *
 * Features:
 * - Focus pull (blur out/in)
 * - Light leak overlay
 * - Chromatic aberration
 * - Color pulse
 * - Smooth crossfade
 */

import React from "react";
import { AbsoluteFill, interpolate, Easing } from "remotion";
import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";

// ============================================
// CINEMATIC TRANSITION PRESENTATION
// ============================================

type CinematicTransitionProps = {
  direction?: "in" | "out";
  accentColor?: string;
  enableBlur?: boolean;
  enableLightLeak?: boolean;
  enableChromatic?: boolean;
  enableColorPulse?: boolean;
};

const CinematicTransitionComponent: React.FC<
  TransitionPresentationComponentProps<CinematicTransitionProps>
> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const {
    accentColor = "#00d9ff",
    enableBlur = true,
    enableLightLeak = true,
    enableChromatic = true,
    enableColorPulse = true,
  } = passedProps;

  const isExiting = presentationDirection === "exiting";
  const progress = presentationProgress;

  // Eased progress for smoother feel
  const easedProgress = Easing.inOut(Easing.cubic)(progress);

  // OPACITY: Crossfade
  const opacity = isExiting
    ? interpolate(easedProgress, [0, 1], [1, 0])
    : interpolate(easedProgress, [0, 1], [0, 1]);

  // BLUR: Focus pull effect - blur peaks at middle of transition
  const blurAmount = enableBlur
    ? Math.sin(progress * Math.PI) * 8
    : 0;

  // SCALE: Slight zoom during blur to hide edges
  const scale = 1 + (blurAmount * 0.005);

  // LIGHT LEAK: Subtle white wash peaks at middle
  const lightLeakOpacity = enableLightLeak
    ? Math.sin(progress * Math.PI) * 0.25
    : 0;

  // Y-OFFSET: Subtle vertical movement
  const yOffset = isExiting
    ? interpolate(easedProgress, [0, 1], [0, -15])
    : interpolate(easedProgress, [0, 1], [15, 0]);

  return (
    <AbsoluteFill>
      {/* Main content with blur and fade */}
      <AbsoluteFill
        style={{
          opacity,
          filter: blurAmount > 0.1 ? `blur(${blurAmount}px)` : "none",
          transform: `scale(${scale}) translateY(${yOffset}px)`,
          transformOrigin: "center center",
        }}
      >
        {children}
      </AbsoluteFill>

      {/* Light leak overlay - subtle white glow */}
      {lightLeakOpacity > 0.01 && (
        <AbsoluteFill
          style={{
            pointerEvents: "none",
            background: isExiting
              ? `linear-gradient(to left, transparent 30%, rgba(255,255,255,${lightLeakOpacity * 0.5}) 50%, transparent 70%)`
              : `linear-gradient(to right, transparent 30%, rgba(255,255,255,${lightLeakOpacity * 0.5}) 50%, transparent 70%)`,
            mixBlendMode: "soft-light",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

/**
 * Create a cinematic transition presentation
 */
export const cinematicFade = (
  props: CinematicTransitionProps = {}
): TransitionPresentation<CinematicTransitionProps> => {
  return {
    component: CinematicTransitionComponent,
    props,
  };
};

// ============================================
// CINEMATIC SLIDE TRANSITION
// ============================================

type CinematicSlideProps = CinematicTransitionProps & {
  slideDirection?: "left" | "right" | "up" | "down";
};

const CinematicSlideComponent: React.FC<
  TransitionPresentationComponentProps<CinematicSlideProps>
> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const {
    slideDirection = "left",
    accentColor = "#00d9ff",
    enableBlur = true,
    enableLightLeak = true,
    enableColorPulse = true,
  } = passedProps;

  const isExiting = presentationDirection === "exiting";
  const progress = presentationProgress;

  // Eased progress
  const easedProgress = Easing.out(Easing.cubic)(progress);

  // Calculate slide offset based on direction
  const slideAmount = 100; // percentage
  let translateX = 0;
  let translateY = 0;

  if (isExiting) {
    switch (slideDirection) {
      case "left":
        translateX = interpolate(easedProgress, [0, 1], [0, -slideAmount]);
        break;
      case "right":
        translateX = interpolate(easedProgress, [0, 1], [0, slideAmount]);
        break;
      case "up":
        translateY = interpolate(easedProgress, [0, 1], [0, -slideAmount]);
        break;
      case "down":
        translateY = interpolate(easedProgress, [0, 1], [0, slideAmount]);
        break;
    }
  } else {
    switch (slideDirection) {
      case "left":
        translateX = interpolate(easedProgress, [0, 1], [slideAmount, 0]);
        break;
      case "right":
        translateX = interpolate(easedProgress, [0, 1], [-slideAmount, 0]);
        break;
      case "up":
        translateY = interpolate(easedProgress, [0, 1], [slideAmount, 0]);
        break;
      case "down":
        translateY = interpolate(easedProgress, [0, 1], [-slideAmount, 0]);
        break;
    }
  }

  // Blur during slide
  const blurAmount = enableBlur
    ? Math.sin(progress * Math.PI) * 4
    : 0;

  // Scale slightly during transition
  const scale = interpolate(
    Math.sin(progress * Math.PI),
    [0, 1],
    [1, 0.98]
  );

  // Light leak
  const lightLeakOpacity = enableLightLeak
    ? Math.sin(progress * Math.PI) * 0.2
    : 0;

  // Color pulse
  const colorPulseOpacity = enableColorPulse
    ? Math.sin(progress * Math.PI) * 0.08
    : 0;

  return (
    <AbsoluteFill>
      {/* Main content with slide, blur, and scale */}
      <AbsoluteFill
        style={{
          filter: blurAmount > 0.1 ? `blur(${blurAmount}px)` : "none",
          transform: `translate(${translateX}%, ${translateY}%) scale(${scale})`,
          transformOrigin: "center center",
        }}
      >
        {children}
      </AbsoluteFill>

      {/* Light leak - subtle white glow */}
      {lightLeakOpacity > 0.01 && (
        <AbsoluteFill
          style={{
            pointerEvents: "none",
            background: `radial-gradient(ellipse at ${isExiting ? '30%' : '70%'} 50%, rgba(255,255,255,${lightLeakOpacity * 0.5}) 0%, transparent 60%)`,
            mixBlendMode: "soft-light",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

/**
 * Create a cinematic slide transition
 */
export const cinematicSlide = (
  props: CinematicSlideProps = {}
): TransitionPresentation<CinematicSlideProps> => {
  return {
    component: CinematicSlideComponent,
    props,
  };
};

export default cinematicFade;
