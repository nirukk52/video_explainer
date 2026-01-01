/**
 * Scene 17: Conclusion - The Full Picture (Enhanced)
 *
 * A triumphant YouTube-worthy finale with:
 * 1. Dramatic speedometer showing 40 → 3500+ tok/s
 * 2. Technique stack animation with icons
 * 3. 87x FASTER reveal with impact effects
 * 4. Animated counters
 * 5. Visual summary tying all concepts together
 */

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
  Easing,
} from "remotion";
import { COLORS as STYLE_COLORS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface ConclusionSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0a0a14",
  backgroundGradient1: "#0f0f1a",
  backgroundGradient2: "#1a0a2e",
  primary: "#00d9ff",
  success: "#00ff88",
  highlight: "#f1c40f",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
  glow: "#00ff88",
  burst: "#ffd700",
};

const TECHNIQUES = [
  { name: "KV Cache", icon: "💾", color: "#9b59b6", benefit: "No redundant computation" },
  { name: "PagedAttention", icon: "📄", color: "#00d9ff", benefit: "95%+ memory efficiency" },
  { name: "Quantization", icon: "🔢", color: "#f1c40f", benefit: "4× smaller models" },
  { name: "Speculative Decoding", icon: "🚀", color: "#ff6b35", benefit: "2-3× faster generation" },
  { name: "Continuous Batching", icon: "⚡", color: "#00ff88", benefit: "100% GPU utilization" },
  { name: "Parallel Scaling", icon: "🌐", color: "#e74c3c", benefit: "Millions of users" },
];

// Animated Counter Component
const AnimatedCounter: React.FC<{
  value: number;
  scale: number;
  color: string;
  suffix?: string;
  fontSize?: number;
}> = ({ value, scale, color, suffix = "", fontSize = 72 }) => {
  return (
    <span
      style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: fontSize * scale,
        fontWeight: 800,
        color,
        textShadow: `0 0 ${20 * scale}px ${color}40, 0 0 ${40 * scale}px ${color}20`,
      }}
    >
      {Math.round(value).toLocaleString()}{suffix}
    </span>
  );
};

// Speedometer Visualization
const SpeedometerVisualization: React.FC<{
  speed: number;
  maxSpeed: number;
  scale: number;
  frame: number;
  fps: number;
}> = ({ speed, maxSpeed, scale, frame, fps }) => {
  const normalizedSpeed = Math.min(speed / maxSpeed, 1);
  const angle = interpolate(normalizedSpeed, [0, 1], [-135, 135]);

  // Color transition from red to green based on speed
  const speedColor = interpolate(
    normalizedSpeed,
    [0, 0.3, 0.7, 1],
    [0, 0, 0, 0]
  );

  const getSpeedColor = () => {
    if (normalizedSpeed < 0.15) return "#ff4757";
    if (normalizedSpeed < 0.4) return "#ffa502";
    if (normalizedSpeed < 0.7) return "#f1c40f";
    return "#00ff88";
  };

  // Pulsing glow effect at high speeds
  const glowPulse = normalizedSpeed > 0.8
    ? interpolate(Math.sin(frame * 0.3), [-1, 1], [0.5, 1])
    : 0.3;

  return (
    <div
      style={{
        position: "relative",
        width: 280 * scale,
        height: 160 * scale,
      }}
    >
      {/* Speedometer arc background */}
      <svg
        width={280 * scale}
        height={160 * scale}
        viewBox="0 0 280 160"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        {/* Background arc */}
        <path
          d="M 30 140 A 110 110 0 0 1 250 140"
          fill="none"
          stroke="#333"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {/* Speed arc */}
        <path
          d="M 30 140 A 110 110 0 0 1 250 140"
          fill="none"
          stroke={getSpeedColor()}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${normalizedSpeed * 345} 345`}
          style={{
            filter: `drop-shadow(0 0 ${10 * glowPulse}px ${getSpeedColor()})`,
          }}
        />
        {/* Speed markers */}
        {[0, 0.25, 0.5, 0.75, 1].map((marker, i) => {
          const markerAngle = interpolate(marker, [0, 1], [-135, 135]) * (Math.PI / 180);
          const x = 140 + 95 * Math.cos(markerAngle - Math.PI / 2);
          const y = 140 + 95 * Math.sin(markerAngle - Math.PI / 2);
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="4"
              fill="#555"
            />
          );
        })}
        {/* Needle */}
        <g transform={`rotate(${angle}, 140, 140)`}>
          <line
            x1="140"
            y1="140"
            x2="140"
            y2="50"
            stroke={getSpeedColor()}
            strokeWidth="4"
            strokeLinecap="round"
            style={{
              filter: `drop-shadow(0 0 8px ${getSpeedColor()})`,
            }}
          />
          <circle
            cx="140"
            cy="140"
            r="12"
            fill={getSpeedColor()}
            style={{
              filter: `drop-shadow(0 0 12px ${getSpeedColor()})`,
            }}
          />
        </g>
      </svg>
    </div>
  );
};

// Technique Stack Item
const TechniqueStackItem: React.FC<{
  technique: typeof TECHNIQUES[0];
  index: number;
  progress: number;
  scale: number;
  isConnected: boolean;
}> = ({ technique, index, progress, scale, isConnected }) => {
  const itemProgress = interpolate(
    progress,
    [index * 0.15, index * 0.15 + 0.12],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const slideIn = interpolate(itemProgress, [0, 1], [-50, 0]);
  const opacity = interpolate(itemProgress, [0, 0.3, 1], [0, 1, 1]);
  const scaleAnim = interpolate(itemProgress, [0, 0.5, 1], [0.5, 1.1, 1]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16 * scale,
        opacity,
        transform: `translateX(${slideIn * scale}px) scale(${scaleAnim})`,
        marginBottom: 12 * scale,
      }}
    >
      {/* Connection line */}
      {index > 0 && (
        <div
          style={{
            position: "absolute",
            left: 20 * scale,
            top: -8 * scale,
            width: 3 * scale,
            height: 16 * scale,
            background: isConnected
              ? `linear-gradient(to bottom, ${TECHNIQUES[index - 1].color}, ${technique.color})`
              : "transparent",
            opacity: isConnected ? 1 : 0,
          }}
        />
      )}
      {/* Icon container */}
      <div
        style={{
          width: 72 * scale,
          height: 72 * scale,
          borderRadius: 14 * scale,
          backgroundColor: technique.color + "25",
          border: `3px solid ${technique.color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 34 * scale,
          boxShadow: itemProgress > 0.8 ? `0 0 ${15 * scale}px ${technique.color}50` : "none",
        }}
      >
        {technique.icon}
      </div>
      {/* Text */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: 26 * scale,
            fontWeight: 700,
            color: technique.color,
          }}
        >
          {technique.name}
        </div>
        <div
          style={{
            fontSize: 18 * scale,
            color: COLORS.textDim,
          }}
        >
          {technique.benefit}
        </div>
      </div>
    </div>
  );
};

// Impact Reveal for 87x FASTER
const ImpactReveal: React.FC<{
  frame: number;
  startFrame: number;
  fps: number;
  scale: number;
}> = ({ frame, startFrame, fps, scale }) => {
  const localFrame = frame - startFrame;

  // Initial burst scale
  const burstScale = spring({
    frame: localFrame,
    fps,
    config: { damping: 8, stiffness: 100, mass: 0.8 },
  });

  // Text scale with overshoot
  const textScale = spring({
    frame: localFrame - 5,
    fps,
    config: { damping: 10, stiffness: 150 },
  });

  // Glow pulse
  const glowIntensity = interpolate(
    Math.sin(localFrame * 0.15),
    [-1, 1],
    [0.6, 1]
  );

  // Particle burst effect
  const particles = Array.from({ length: 12 }).map((_, i) => {
    const angle = (i / 12) * Math.PI * 2;
    const distance = interpolate(localFrame, [0, 20], [0, 150], {
      extrapolateRight: "clamp",
    });
    const particleOpacity = interpolate(localFrame, [0, 5, 25], [0, 1, 0], {
      extrapolateRight: "clamp",
    });
    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
      opacity: particleOpacity,
    };
  });

  if (localFrame < 0) return null;

  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Particle burst */}
      {particles.map((particle, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            width: 8 * scale,
            height: 8 * scale,
            borderRadius: "50%",
            backgroundColor: COLORS.burst,
            transform: `translate(${particle.x * scale}px, ${particle.y * scale}px)`,
            opacity: particle.opacity,
            boxShadow: `0 0 ${10 * scale}px ${COLORS.burst}`,
          }}
        />
      ))}

      {/* Glow ring */}
      <div
        style={{
          position: "absolute",
          width: 320 * scale * burstScale,
          height: 320 * scale * burstScale,
          borderRadius: "50%",
          border: `3px solid ${COLORS.success}30`,
          boxShadow: `0 0 ${60 * glowIntensity * scale}px ${COLORS.success}40, inset 0 0 ${40 * glowIntensity * scale}px ${COLORS.success}20`,
          opacity: interpolate(localFrame, [0, 30], [0.8, 0.3], { extrapolateRight: "clamp" }),
        }}
      />

      {/* Main text container */}
      <div
        style={{
          transform: `scale(${textScale})`,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 100 * scale,
            fontWeight: 900,
            fontFamily: "Inter, sans-serif",
            background: `linear-gradient(135deg, ${COLORS.success}, ${COLORS.primary}, ${COLORS.burst})`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            textShadow: `0 0 ${40 * glowIntensity * scale}px ${COLORS.success}60`,
            letterSpacing: -4 * scale,
          }}
        >
          87×
        </div>
        <div
          style={{
            fontSize: 48 * scale,
            fontWeight: 800,
            color: COLORS.success,
            textShadow: `0 0 ${30 * glowIntensity * scale}px ${COLORS.success}80`,
            marginTop: -10 * scale,
            letterSpacing: 8 * scale,
          }}
        >
          FASTER
        </div>
      </div>
    </div>
  );
};

// Visual Summary Component
const VisualSummary: React.FC<{
  progress: number;
  scale: number;
  frame: number;
}> = ({ progress, scale, frame }) => {
  const summaryItems = [
    { icon: "🔋", label: "Memory-Bound", sublabel: "Not Compute" },
    { icon: "📦", label: "Batch Smart", sublabel: "Max Throughput" },
    { icon: "🧠", label: "Cache Everything", sublabel: "Zero Waste" },
    { icon: "⚡", label: "Scale Infinitely", sublabel: "Any Load" },
  ];

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: 32 * scale,
        opacity: interpolate(progress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
      }}
    >
      {summaryItems.map((item, i) => {
        const itemDelay = i * 0.15;
        const itemProgress = interpolate(
          progress,
          [itemDelay, itemDelay + 0.2],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        const bounce = spring({
          frame: frame - Math.round(itemDelay * 60),
          fps: 30,
          config: { damping: 8, stiffness: 200 },
        });

        return (
          <div
            key={i}
            style={{
              textAlign: "center",
              opacity: itemProgress,
              transform: `scale(${bounce}) translateY(${(1 - itemProgress) * 20}px)`,
            }}
          >
            <div
              style={{
                fontSize: 48 * scale,
                marginBottom: 10 * scale,
              }}
            >
              {item.icon}
            </div>
            <div
              style={{
                fontSize: 22 * scale,
                fontWeight: 700,
                color: COLORS.primary,
              }}
            >
              {item.label}
            </div>
            <div
              style={{
                fontSize: 17 * scale,
                color: COLORS.textDim,
              }}
            >
              {item.sublabel}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// Racing Graph Component
const RacingGraph: React.FC<{
  slowSpeed: number;
  fastSpeed: number;
  scale: number;
  frame: number;
}> = ({ slowSpeed, fastSpeed, scale, frame }) => {
  const maxSpeed = 4000;
  const slowWidth = (slowSpeed / maxSpeed) * 100;
  const fastWidth = (fastSpeed / maxSpeed) * 100;

  const pulse = interpolate(Math.sin(frame * 0.2), [-1, 1], [0.9, 1.1]);

  return (
    <div style={{ width: "100%", padding: `0 ${20 * scale}px` }}>
      {/* Slow bar */}
      <div style={{ marginBottom: 16 * scale }}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6 * scale,
        }}>
          <span style={{ fontSize: 20 * scale, color: COLORS.textDim }}>Naive</span>
          <span style={{ fontSize: 22 * scale, color: "#ff4757", fontWeight: 700, fontFamily: "JetBrains Mono" }}>
            {Math.round(slowSpeed)} tok/s
          </span>
        </div>
        <div
          style={{
            height: 24 * scale,
            backgroundColor: "#1a1a2e",
            borderRadius: 12 * scale,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${slowWidth}%`,
              backgroundColor: "#ff4757",
              borderRadius: 8 * scale,
              boxShadow: `0 0 ${10 * scale}px #ff475750`,
            }}
          />
        </div>
      </div>
      {/* Fast bar */}
      <div>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6 * scale,
        }}>
          <span style={{ fontSize: 20 * scale, color: COLORS.textDim }}>Optimized</span>
          <span style={{
            fontSize: 22 * scale,
            color: COLORS.success,
            fontWeight: 700,
            fontFamily: "JetBrains Mono",
            transform: fastSpeed > 3000 ? `scale(${pulse})` : "none",
            display: "inline-block",
          }}>
            {Math.round(fastSpeed).toLocaleString()}+ tok/s
          </span>
        </div>
        <div
          style={{
            height: 24 * scale,
            backgroundColor: "#1a1a2e",
            borderRadius: 12 * scale,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${fastWidth}%`,
              background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.success})`,
              borderRadius: 8 * scale,
              boxShadow: `0 0 ${15 * scale}px ${COLORS.success}60`,
            }}
          />
        </div>
      </div>
    </div>
  );
};

export const ConclusionScene: React.FC<ConclusionSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Responsive scaling
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings (restructured for new visual elements)
  const phase1End = Math.round(durationInFrames * 0.22);   // Speedometer + racing graph
  const phase2End = Math.round(durationInFrames * 0.50);   // Technique stack
  const phase3End = Math.round(durationInFrames * 0.70);   // 87x FASTER reveal
  const phase4End = Math.round(durationInFrames * 1.00);   // Visual summary + CTA

  // Speed counter animations with easing
  const speedAnimProgress = interpolate(
    localFrame,
    [Math.round(durationInFrames * 0.02), Math.round(durationInFrames * 0.18)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const slowSpeed = interpolate(
    speedAnimProgress,
    [0, 0.2, 1],
    [0, 40, 40]
  );

  const fastSpeed = interpolate(
    speedAnimProgress,
    [0, 0.2, 1],
    [0, 40, 3500],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Technique stack progress
  const stackProgress = interpolate(
    localFrame,
    [phase1End, phase2End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Visual summary progress
  const summaryProgress = interpolate(
    localFrame,
    [phase3End + Math.round(durationInFrames * 0.08), phase4End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Animations
  const introOpacity = interpolate(localFrame, [0, Math.round(durationInFrames * 0.02)], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Background gradient animation
  const bgHue = interpolate(localFrame, [0, durationInFrames], [240, 280]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, hsl(${bgHue}, 30%, 12%) 0%, ${COLORS.background} 70%)`,
        fontFamily: "Inter, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Animated background particles */}
      {Array.from({ length: 20 }).map((_, i) => {
        const particleX = interpolate(
          (localFrame + i * 30) % 200,
          [0, 200],
          [-10, 110]
        );
        const particleY = 20 + (i * 47) % 80;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${particleX}%`,
              top: `${particleY}%`,
              width: 4 * scale,
              height: 4 * scale,
              borderRadius: "50%",
              backgroundColor: COLORS.primary,
              opacity: 0.1,
            }}
          />
        );
      })}

      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: introOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>16</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 30 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: introOpacity,
        }}
      >
        <h1
          style={{
            fontSize: 48 * scale,
            fontWeight: 700,
            color: STYLE_COLORS.primary,
            margin: 0,
            letterSpacing: -1 * scale,
          }}
        >
          The Complete Optimization Stack
        </h1>
      </div>

      {/* Main content grid */}
      <div
        style={{
          position: "absolute",
          top: 90 * scale,
          left: 60 * scale,
          right: 60 * scale,
          bottom: 60 * scale,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "auto 1fr auto",
          gap: 24 * scale,
          opacity: introOpacity,
        }}
      >
        {/* Left: Speed Visualization */}
        <div
          style={{
            gridColumn: "1",
            gridRow: "1",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16 * scale,
          }}
        >
          <SpeedometerVisualization
            speed={fastSpeed}
            maxSpeed={4000}
            scale={scale}
            frame={localFrame}
            fps={fps}
          />
          <RacingGraph
            slowSpeed={slowSpeed}
            fastSpeed={fastSpeed}
            scale={scale}
            frame={localFrame}
          />
        </div>

        {/* Right: Technique Stack */}
        <div
          style={{
            gridColumn: "2",
            gridRow: "1 / 3",
            padding: 20 * scale,
            backgroundColor: COLORS.surface + "80",
            borderRadius: 16 * scale,
            border: `1px solid ${COLORS.primary}30`,
          }}
        >
          <div
            style={{
              fontSize: 22 * scale,
              fontWeight: 700,
              color: COLORS.primary,
              marginBottom: 20 * scale,
              textTransform: "uppercase",
              letterSpacing: 3 * scale,
            }}
          >
            Optimization Stack
          </div>
          <div style={{ position: "relative" }}>
            {TECHNIQUES.map((tech, index) => (
              <TechniqueStackItem
                key={tech.name}
                technique={tech}
                index={index}
                progress={stackProgress}
                scale={scale}
                isConnected={stackProgress > (index + 1) * 0.15}
              />
            ))}
          </div>
        </div>

        {/* Left bottom: 87x FASTER reveal */}
        <div
          style={{
            gridColumn: "1",
            gridRow: "2",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {localFrame >= phase2End && (
            <ImpactReveal
              frame={localFrame}
              startFrame={phase2End}
              fps={fps}
              scale={scale}
            />
          )}
        </div>

        {/* Bottom: Visual Summary */}
        <div
          style={{
            gridColumn: "1 / 3",
            gridRow: "3",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16 * scale,
          }}
        >
          <VisualSummary
            progress={summaryProgress}
            scale={scale}
            frame={localFrame}
          />

          {/* Final CTA */}
          <div
            style={{
              opacity: interpolate(
                localFrame,
                [phase4End - Math.round(durationInFrames * 0.1), phase4End - Math.round(durationInFrames * 0.05)],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              ),
              transform: `scale(${spring({
                frame: localFrame - (phase4End - Math.round(durationInFrames * 0.1)),
                fps,
                config: { damping: 12, stiffness: 200 },
              })})`,
            }}
          >
            <div
              style={{
                display: "inline-block",
                background: `linear-gradient(135deg, ${COLORS.success}20, ${COLORS.primary}20)`,
                border: `2px solid ${COLORS.success}`,
                borderRadius: 16 * scale,
                padding: `${16 * scale}px ${32 * scale}px`,
                boxShadow: `0 0 ${40 * scale}px ${COLORS.success}30`,
              }}
            >
              <div
                style={{
                  fontSize: 24 * scale,
                  fontWeight: 700,
                  color: COLORS.success,
                  textAlign: "center",
                }}
              >
                These techniques power every major AI service
              </div>
              <div
                style={{
                  fontSize: 18 * scale,
                  color: COLORS.textDim,
                  marginTop: 8 * scale,
                  textAlign: "center",
                  letterSpacing: 4 * scale,
                }}
              >
                GPT-4 • Claude • Gemini • LLaMA • Mistral
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default ConclusionScene;
