/**
 * CinematicEffects - Visual effects for a film-like feel
 *
 * Includes:
 * - Persistent floating particles
 * - Subtle camera breathing/drift
 * - Vignette overlay
 * - Light leaks during transitions
 * - Chromatic aberration
 */

import React, { useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  random,
} from "remotion";

// ============================================
// PERSISTENT PARTICLES
// ============================================

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  drift: number;
}

export const PersistentParticles: React.FC<{
  count?: number;
  color?: string;
  seed?: string;
}> = ({ count = 30, color = "#ffffff", seed = "particles" }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const particles = useMemo<Particle[]>(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      x: random(`${seed}-x-${i}`) * width,
      y: random(`${seed}-y-${i}`) * height,
      size: 1 + random(`${seed}-size-${i}`) * 3,
      speed: 0.1 + random(`${seed}-speed-${i}`) * 0.3,
      opacity: 0.1 + random(`${seed}-opacity-${i}`) * 0.2,
      drift: (random(`${seed}-drift-${i}`) - 0.5) * 0.5,
    }));
  }, [count, width, height, seed]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 1000 }}>
      {particles.map((p) => {
        // Slow upward drift with horizontal sway
        const yOffset = (frame * p.speed) % (height + 100);
        const xOffset = Math.sin(frame * 0.01 + p.id) * 30 * p.drift;
        const y = (p.y - yOffset + height + 100) % (height + 100) - 50;
        const x = p.x + xOffset;

        // Subtle twinkle
        const twinkle = 0.7 + Math.sin(frame * 0.05 + p.id * 2) * 0.3;

        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              backgroundColor: color,
              opacity: p.opacity * twinkle,
              filter: `blur(${p.size * 0.3}px)`,
              boxShadow: `0 0 ${p.size * 2}px ${color}`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ============================================
// CAMERA BREATHING & DRIFT
// ============================================

export const CameraBreathing: React.FC<{
  children: React.ReactNode;
  intensity?: number; // 0-1, default 0.5
  speed?: number; // oscillation speed, default 0.02
}> = ({ children, intensity = 0.5, speed = 0.015 }) => {
  const frame = useCurrentFrame();

  // Gentle zoom oscillation (breathing)
  const breathe = Math.sin(frame * speed) * (0.008 * intensity);
  const scale = 1 + breathe;

  // Subtle drift
  const driftX = Math.sin(frame * speed * 0.7) * (3 * intensity);
  const driftY = Math.cos(frame * speed * 0.5) * (2 * intensity);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        transform: `scale(${scale}) translate(${driftX}px, ${driftY}px)`,
        transformOrigin: "center center",
      }}
    >
      {children}
    </div>
  );
};

// ============================================
// VIGNETTE OVERLAY
// ============================================

export const Vignette: React.FC<{
  intensity?: number; // 0-1, default 0.4
}> = ({ intensity = 0.4 }) => {
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 999,
        background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${intensity}) 100%)`,
      }}
    />
  );
};

// ============================================
// AMBIENT GLOW LAYER
// ============================================

export const AmbientGlow: React.FC<{
  color?: string;
  intensity?: number;
}> = ({ color = "#00d9ff", intensity = 0.15 }) => {
  const frame = useCurrentFrame();

  // Subtle pulsing
  const pulse = 0.7 + Math.sin(frame * 0.02) * 0.3;
  const opacity = intensity * pulse;

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 1,
        background: `radial-gradient(ellipse at 50% 120%, ${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')} 0%, transparent 60%)`,
      }}
    />
  );
};

// ============================================
// LIGHT LEAK OVERLAY (for transitions)
// ============================================

export const LightLeak: React.FC<{
  progress: number; // 0-1, transition progress
  direction?: "left" | "right" | "top" | "bottom";
  color?: string;
}> = ({ progress, direction = "right", color = "#fff8e7" }) => {
  // Light leak peaks at middle of transition
  const intensity = Math.sin(progress * Math.PI) * 0.4;

  if (intensity < 0.01) return null;

  const gradientDirection = {
    left: "to right",
    right: "to left",
    top: "to bottom",
    bottom: "to top",
  }[direction];

  const position = interpolate(progress, [0, 1], [-50, 150]);

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 1001,
        background: `linear-gradient(${gradientDirection}, transparent ${position - 30}%, ${color} ${position}%, transparent ${position + 30}%)`,
        opacity: intensity,
        mixBlendMode: "overlay",
      }}
    />
  );
};

// ============================================
// CHROMATIC ABERRATION (for transitions)
// ============================================

export const ChromaticAberration: React.FC<{
  children: React.ReactNode;
  intensity: number; // 0-1, typically tied to transition progress
}> = ({ children, intensity }) => {
  // Peak aberration at middle of transition
  const aberrationAmount = Math.sin(intensity * Math.PI) * 4;

  if (aberrationAmount < 0.1) {
    return <>{children}</>;
  }

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {/* Red channel - shifted left */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: -aberrationAmount,
          right: aberrationAmount,
          bottom: 0,
          filter: "url(#red-channel)",
          opacity: 0.5,
          mixBlendMode: "screen",
        }}
      >
        {children}
      </div>
      {/* Blue channel - shifted right */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: aberrationAmount,
          right: -aberrationAmount,
          bottom: 0,
          filter: "url(#blue-channel)",
          opacity: 0.5,
          mixBlendMode: "screen",
        }}
      >
        {children}
      </div>
      {/* Main content */}
      <div style={{ position: "relative" }}>{children}</div>

      {/* SVG filters for color separation */}
      <svg style={{ position: "absolute", width: 0, height: 0 }}>
        <defs>
          <filter id="red-channel">
            <feColorMatrix
              type="matrix"
              values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
            />
          </filter>
          <filter id="blue-channel">
            <feColorMatrix
              type="matrix"
              values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
            />
          </filter>
        </defs>
      </svg>
    </div>
  );
};

// ============================================
// COLOR PULSE (signature color during transitions)
// ============================================

export const ColorPulse: React.FC<{
  progress: number; // 0-1, transition progress
  color?: string;
}> = ({ progress, color = "#00d9ff" }) => {
  // Pulse peaks at middle of transition
  const intensity = Math.sin(progress * Math.PI) * 0.15;

  if (intensity < 0.01) return null;

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 1002,
        backgroundColor: color,
        opacity: intensity,
        mixBlendMode: "color-dodge",
      }}
    />
  );
};

// ============================================
// DESATURATION EFFECT (during transitions)
// ============================================

export const DesaturationOverlay: React.FC<{
  progress: number; // 0-1, transition progress
}> = ({ progress }) => {
  // Peak desaturation at middle of transition
  const desaturation = Math.sin(progress * Math.PI) * 0.3;

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 998,
        backdropFilter: `saturate(${1 - desaturation})`,
      }}
    />
  );
};

// ============================================
// FOCUS BLUR (for focus pull transitions)
// ============================================

export const FocusBlur: React.FC<{
  children: React.ReactNode;
  blurAmount: number; // 0-20px typically
}> = ({ children, blurAmount }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        filter: blurAmount > 0.1 ? `blur(${blurAmount}px)` : "none",
        transform: blurAmount > 0.1 ? `scale(${1 + blurAmount * 0.01})` : "none", // Slight zoom to hide blur edges
      }}
    >
      {children}
    </div>
  );
};

// ============================================
// COMBINED CINEMATIC WRAPPER
// ============================================

export const CinematicWrapper: React.FC<{
  children: React.ReactNode;
  enableBreathing?: boolean;
  enableVignette?: boolean;
  enableParticles?: boolean;
  enableAmbientGlow?: boolean;
  particleColor?: string;
  glowColor?: string;
}> = ({
  children,
  enableBreathing = true,
  enableVignette = true,
  enableParticles = true,
  enableAmbientGlow = true,
  particleColor = "#ffffff",
  glowColor = "#00d9ff",
}) => {
  return (
    <AbsoluteFill>
      {enableAmbientGlow && <AmbientGlow color={glowColor} />}

      {enableBreathing ? (
        <CameraBreathing>
          {children}
        </CameraBreathing>
      ) : (
        children
      )}

      {enableParticles && <PersistentParticles color={particleColor} />}
      {enableVignette && <Vignette />}
    </AbsoluteFill>
  );
};

export default CinematicWrapper;
