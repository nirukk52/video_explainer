/**
 * Scene 1: The Speed Problem (Hook)
 *
 * Goal: Grab attention with the dramatic speed difference
 * 40 tokens/second → 3,500 tokens/second = 87x improvement
 *
 * Visual flow:
 * 1. Show a prompt being typed
 * 2. Racing bar chart with slow red bar (40 tok/s)
 * 3. Dramatic burst animation for fast speed (3500+ tok/s)
 * 4. Animated flying token counter
 * 5. 87x reveal with zoom/pulse effect
 *
 * Layout: Speed indicator on left, 87x badge on right (non-overlapping)
 */

import React, { useMemo } from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";
import { COLORS as STYLE_COLORS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface HookSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  secondary: "#ff6b35",
  slowRed: "#ff3b3b",
  success: "#00ff88",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
};

const PROMPT = "Explain how transformers work";
const RESPONSE_TOKENS = [
  "Transformers", "are", "neural", "networks", "that", "use",
  "attention", "mechanisms", "to", "process", "sequences", "in", "parallel,",
  "enabling", "much", "faster", "training", "and", "inference", "compared",
  "to", "recurrent", "neural", "networks.", "The", "key", "innovation",
  "is", "the", "self-attention", "mechanism,", "which", "allows", "each",
  "token", "to", "attend", "to", "every", "other", "token", "in", "the",
  "sequence.", "This", "parallel", "processing", "capability", "makes",
  "transformers", "ideal", "for", "modern", "hardware", "like", "GPUs",
  "and", "TPUs,", "enabling", "massive", "speedups", "in", "both",
  "training", "and", "inference", "workloads.", "Combined", "with",
  "techniques", "like", "KV", "caching,", "batching,", "and", "quantization,",
  "modern", "LLMs", "can", "achieve", "remarkable", "throughput.",
];

// Particle component for burst effect
const Particle: React.FC<{
  index: number;
  frame: number;
  startFrame: number;
  scale: number;
  baseX: number;
  baseY: number;
}> = ({ index, frame, startFrame, scale, baseX, baseY }) => {
  const localFrame = frame - startFrame;
  if (localFrame < 0) return null;

  const angle = (index * 137.5) % 360; // Golden angle for distribution
  const speed = 3 + (index % 5) * 1.5;
  const distance = localFrame * speed;
  const opacity = interpolate(localFrame, [0, 30], [1, 0], { extrapolateRight: "clamp" });

  const x = baseX + Math.cos((angle * Math.PI) / 180) * distance;
  const y = baseY + Math.sin((angle * Math.PI) / 180) * distance;
  const size = (3 + (index % 3)) * scale;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: COLORS.success,
        opacity,
        boxShadow: `0 0 ${6 * scale}px ${COLORS.success}`,
      }}
    />
  );
};

export const HookScene: React.FC<HookSceneProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Responsive scaling based on 1920x1080 reference
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings - proportional to total scene duration
  const phase1End = Math.round(durationInFrames * 0.10); // Show prompt (~10%)
  const phase2Start = phase1End;
  const phase2End = Math.round(durationInFrames * 0.40); // Slow bar grows (~40%)
  const phase3Start = phase2End;
  const phase3End = Math.round(durationInFrames * 0.55); // Pause, then fast bar (~55%)
  const phase4Start = phase3End;
  const phase4End = Math.round(durationInFrames * 0.75); // Fast bar bursts (~75%)
  const phase5Start = phase4End;
  const phase5End = Math.round(durationInFrames * 1.00); // 87x reveal (100%)

  // Prompt typing animation
  const promptProgress = interpolate(localFrame, [0, phase1End], [0, 1], {
    extrapolateRight: "clamp",
  });
  const visiblePromptChars = Math.floor(promptProgress * PROMPT.length);

  // Slow bar animation (red, grows slowly)
  const slowBarProgress = interpolate(
    localFrame,
    [phase2Start, phase2End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const slowBarWidth = interpolate(slowBarProgress, [0, 1], [0, 40], {
    extrapolateRight: "clamp",
  });

  // Slow speed counter
  const slowSpeed = interpolate(
    localFrame,
    [phase2Start + 10, phase2End],
    [0, 40],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Fast bar animation (green, bursts dramatically)
  const showFastBar = localFrame > phase3Start;
  const fastBarDelay = phase3Start;

  const fastBarSpring = spring({
    frame: localFrame - fastBarDelay,
    fps,
    config: { damping: 8, stiffness: 80, mass: 0.5 },
  });

  const fastBarWidth = showFastBar
    ? interpolate(fastBarSpring, [0, 1], [0, 350], { extrapolateRight: "clamp" })
    : 0;

  // Fast speed counter with dramatic acceleration
  const fastSpeed = interpolate(
    localFrame,
    [phase3Start, phase4End],
    [40, 3500],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Burst effect timing
  const burstStartFrame = phase3Start + 5;
  const showBurst = localFrame > burstStartFrame && localFrame < burstStartFrame + 40;

  // Glow intensity for fast bar
  const fastBarGlow = showFastBar
    ? interpolate(
      Math.sin((localFrame - phase3Start) * 0.2),
      [-1, 1],
      [0.5, 1]
    )
    : 0;

  // Scale pulse for fast bar entrance
  const fastBarScale = showFastBar
    ? spring({
      frame: localFrame - phase3Start,
      fps,
      config: { damping: 10, stiffness: 150 },
    })
    : 0;

  // 87x reveal with enhanced zoom/pulse
  const revealStartFrame = phase5Start;
  const revealProgress = interpolate(
    localFrame,
    [revealStartFrame, revealStartFrame + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const revealScale = spring({
    frame: localFrame - revealStartFrame,
    fps,
    config: { damping: 8, stiffness: 100, mass: 1.2 },
  });

  // Enhanced pulse effect for 87x (multiple pulses)
  const pulseFrame = localFrame - revealStartFrame;
  const glowPulse = revealProgress > 0
    ? interpolate(
      Math.sin(pulseFrame * 0.12),
      [-1, 1],
      [0.6, 1.2]
    )
    : 0;

  // Zoom effect on reveal
  const zoomScale = revealProgress > 0
    ? 1 + interpolate(
      Math.sin(pulseFrame * 0.08),
      [-1, 1],
      [0, 0.08]
    ) * glowPulse
    : 1;

  // Generate particle positions
  const particles = useMemo(() => {
    return Array.from({ length: 24 }, (_, i) => i);
  }, []);

  // Bar chart dimensions
  const barChartWidth = 500 * scale;
  const barHeight = 50 * scale;
  const maxBarValue = 350;

  // Current mode
  const showingFast = localFrame > phase3Start;
  const currentSpeed = showingFast ? fastSpeed : slowSpeed;

  // Calculate visible tokens for streaming text effect
  // Slow phase: 8-10 frames per word, Fast phase: 1-2 frames per word
  const SLOW_FRAMES_PER_WORD = 9;
  const FAST_FRAMES_PER_WORD = 1.5;

  const visibleTokenCount = useMemo(() => {
    if (localFrame < phase2Start) return 0;

    // Calculate tokens shown during slow phase
    const slowPhaseFrames = Math.max(0, Math.min(localFrame - phase2Start, phase2End - phase2Start));
    const slowTokens = Math.floor(slowPhaseFrames / SLOW_FRAMES_PER_WORD);

    if (localFrame <= phase2End) {
      return Math.min(slowTokens, RESPONSE_TOKENS.length);
    }

    // Fast phase: continue from where slow phase left off
    const tokensAtSlowEnd = Math.floor((phase2End - phase2Start) / SLOW_FRAMES_PER_WORD);
    const fastPhaseFrames = localFrame - phase3Start;
    const fastTokens = Math.floor(fastPhaseFrames / FAST_FRAMES_PER_WORD);

    return Math.min(tokensAtSlowEnd + fastTokens, RESPONSE_TOKENS.length);
  }, [localFrame, phase2Start, phase2End, phase3Start]);

  // Get the visible response text
  const visibleResponseText = useMemo(() => {
    return RESPONSE_TOKENS.slice(0, visibleTokenCount).join(' ');
  }, [visibleTokenCount]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: interpolate(localFrame, [0, 15], [0, 1]) }}>
        <span style={getSceneIndicatorTextStyle(scale)}>1</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 50 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: interpolate(localFrame, [0, 15], [0, 1]),
        }}
      >
        <h1
          style={{
            fontSize: 48 * scale,
            fontWeight: 700,
            color: STYLE_COLORS.primary,
            margin: 0,
          }}
        >
          LLM Inference
        </h1>
        <p
          style={{
            fontSize: 22 * scale,
            color: COLORS.textDim,
            marginTop: 6 * scale,
          }}
        >
          How fast can we generate tokens?
        </p>
      </div>

      {/* Chat interface - positioned higher */}
      <div
        style={{
          position: "absolute",
          top: 150 * scale,
          left: "50%",
          transform: "translateX(-50%)",
          width: Math.min(900 * scale, width * 0.85),
        }}
      >
        {/* User prompt */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            marginBottom: 16 * scale,
          }}
        >
          <div
            style={{
              backgroundColor: COLORS.primary + "30",
              border: `1px solid ${COLORS.primary}50`,
              borderRadius: 12 * scale,
              borderBottomRightRadius: 4 * scale,
              padding: `${12 * scale}px ${18 * scale}px`,
              maxWidth: "70%",
            }}
          >
            <span
              style={{
                fontSize: 18 * scale,
                color: COLORS.text,
              }}
            >
              {PROMPT.slice(0, visiblePromptChars)}
              <span
                style={{
                  opacity: Math.sin(localFrame * 0.3) > 0 ? 1 : 0,
                  color: COLORS.primary,
                }}
              >
                |
              </span>
            </span>
          </div>
        </div>

        {/* AI response with streaming text */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-start",
            opacity: localFrame > phase1End ? 1 : 0,
          }}
        >
          <div
            style={{
              backgroundColor: COLORS.surface,
              border: `1px solid ${showingFast ? COLORS.success + '40' : '#333'}`,
              borderRadius: 12 * scale,
              borderBottomLeftRadius: 4 * scale,
              padding: `${14 * scale}px ${20 * scale}px`,
              minWidth: 200 * scale,
              maxWidth: "90%",
              minHeight: 50 * scale,
              maxHeight: 280 * scale,
              overflow: "hidden",
              transition: "border-color 0.3s ease",
            }}
          >
            {visibleTokenCount === 0 ? (
              // Show loading indicator before text starts
              <div style={{ display: "flex", alignItems: "center", gap: 8 * scale }}>
                <span
                  style={{
                    fontSize: 16 * scale,
                    color: COLORS.textDim,
                  }}
                >
                  Thinking
                </span>
                <span
                  style={{
                    fontSize: 16 * scale,
                    color: COLORS.textDim,
                    opacity: Math.sin(localFrame * 0.2) > 0 ? 1 : 0.3,
                  }}
                >
                  ●●●
                </span>
              </div>
            ) : (
              // Show streaming text
              <div
                style={{
                  fontSize: 18 * scale,
                  lineHeight: 1.5,
                  color: COLORS.text,
                  wordWrap: "break-word",
                }}
              >
                <span
                  style={{
                    color: showingFast ? COLORS.text : COLORS.text,
                  }}
                >
                  {visibleResponseText}
                </span>
                {/* Blinking cursor at end */}
                <span
                  style={{
                    color: showingFast ? COLORS.success : COLORS.slowRed,
                    opacity: Math.sin(localFrame * 0.3) > 0 ? 1 : 0.3,
                    fontWeight: 700,
                    marginLeft: 2 * scale,
                    textShadow: showingFast ? `0 0 ${8 * scale}px ${COLORS.success}` : 'none',
                  }}
                >
                  |
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Racing Bar Chart - Center focus */}
      <div
        style={{
          position: "absolute",
          top: "58%",
          left: "50%",
          transform: "translate(-50%, -30%)",
          width: barChartWidth + 200 * scale,
          opacity: localFrame > phase2Start ? 1 : 0,
        }}
      >
        {/* Chart title */}
        <div
          style={{
            textAlign: "center",
            marginBottom: 30 * scale,
            fontSize: 24 * scale,
            color: COLORS.text,
            fontWeight: 600,
          }}
        >
          Token Generation Speed
        </div>

        {/* Slow bar (Naive) */}
        <div style={{ marginBottom: 25 * scale }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: 8 * scale,
            }}
          >
            <span
              style={{
                fontSize: 16 * scale,
                color: COLORS.slowRed,
                fontWeight: 600,
                width: 120 * scale,
              }}
            >
              Naive
            </span>
            <span
              style={{
                fontSize: 18 * scale,
                color: COLORS.textDim,
              }}
            >
              40 tok/s
            </span>
          </div>
          <div
            style={{
              position: "relative",
              height: barHeight,
              backgroundColor: "#1a1a2e",
              borderRadius: 8 * scale,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${(slowBarWidth / maxBarValue) * 100}%`,
                backgroundColor: COLORS.slowRed,
                borderRadius: 8 * scale,
                boxShadow: `0 0 ${10 * scale}px ${COLORS.slowRed}40`,
                transition: "width 0.1s ease-out",
              }}
            />
          </div>
        </div>

        {/* Fast bar (Optimized) - with burst animation */}
        <div style={{ marginBottom: 20 * scale }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginBottom: 8 * scale,
              opacity: showFastBar ? 1 : 0.3,
            }}
          >
            <span
              style={{
                fontSize: 16 * scale,
                color: COLORS.success,
                fontWeight: 600,
                width: 120 * scale,
              }}
            >
              Optimized
            </span>
            <span
              style={{
                fontSize: 18 * scale,
                color: showFastBar ? COLORS.success : COLORS.textDim,
                fontWeight: showFastBar ? 700 : 400,
                textShadow: showFastBar
                  ? `0 0 ${10 * scale}px ${COLORS.success}`
                  : "none",
              }}
            >
              3,500+ tok/s
            </span>
          </div>
          <div
            style={{
              position: "relative",
              height: barHeight,
              backgroundColor: "#1a1a2e",
              borderRadius: 8 * scale,
              overflow: "visible",
            }}
          >
            {/* Fast bar with glow and scale effect */}
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${(fastBarWidth / maxBarValue) * 100}%`,
                backgroundColor: COLORS.success,
                borderRadius: 8 * scale,
                transform: `scaleY(${0.8 + fastBarScale * 0.2})`,
                transformOrigin: "left center",
                boxShadow: showFastBar
                  ? `0 0 ${20 * fastBarGlow * scale}px ${COLORS.success},
                     0 0 ${40 * fastBarGlow * scale}px ${COLORS.success}60,
                     0 0 ${60 * fastBarGlow * scale}px ${COLORS.success}30`
                  : "none",
              }}
            />

            {/* Burst particles */}
            {showBurst &&
              particles.map((i) => (
                <Particle
                  key={i}
                  index={i}
                  frame={localFrame}
                  startFrame={burstStartFrame}
                  scale={scale}
                  baseX={fastBarWidth * scale * (barChartWidth / (maxBarValue * scale))}
                  baseY={barHeight / 2}
                />
              ))}
          </div>
        </div>

        {/* Scale indicator */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 16 * scale,
            color: COLORS.textDim,
            marginTop: 10 * scale,
          }}
        >
          <span>0</span>
          <span>1000</span>
          <span>2000</span>
          <span>3500+ tok/s</span>
        </div>
      </div>

      {/* Speed indicator - Bottom left */}
      <div
        style={{
          position: "absolute",
          bottom: height * 0.08,
          left: 60 * scale,
          textAlign: "left",
          opacity: localFrame > phase2Start ? 1 : 0,
        }}
      >
        <div
          style={{
            fontSize: 16 * scale,
            color: COLORS.textDim,
            marginBottom: 6 * scale,
          }}
        >
          {showingFast ? "Optimized Speed" : "Naive Approach"}
        </div>
        <div
          style={{
            fontSize: 64 * scale,
            fontWeight: 700,
            fontFamily: "JetBrains Mono, monospace",
            color: showingFast ? COLORS.success : COLORS.slowRed,
            textShadow: showingFast
              ? `0 0 ${20 * scale}px ${COLORS.success}60`
              : `0 0 ${10 * scale}px ${COLORS.slowRed}40`,
          }}
        >
          {Math.round(currentSpeed).toLocaleString()}
        </div>
        <div
          style={{
            fontSize: 20 * scale,
            color: COLORS.textDim,
          }}
        >
          tokens/second
        </div>
      </div>

      {/* 87x faster reveal - Enhanced with zoom/pulse effect */}
      {revealProgress > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: height * 0.08,
            right: 60 * scale,
            textAlign: "right",
            opacity: revealProgress,
            transform: `scale(${(0.3 + revealScale * 0.7) * zoomScale})`,
            transformOrigin: "right center",
          }}
        >
          <div
            style={{
              display: "inline-block",
              backgroundColor: COLORS.success + "20",
              border: `${6 * scale}px solid ${COLORS.success}`,
              borderRadius: 24 * scale,
              padding: `${28 * scale}px ${60 * scale}px`,
              boxShadow: `
                0 0 ${40 * glowPulse * scale}px rgba(0, 255, 136, ${0.6 * glowPulse}),
                0 0 ${80 * glowPulse * scale}px rgba(0, 255, 136, ${0.4 * glowPulse}),
                0 0 ${120 * glowPulse * scale}px rgba(0, 255, 136, ${0.2 * glowPulse}),
                inset 0 0 ${30 * glowPulse * scale}px rgba(0, 255, 136, ${0.15 * glowPulse})
              `,
            }}
          >
            <span
              style={{
                fontSize: 88 * scale,
                fontWeight: 800,
                color: COLORS.success,
                textShadow: `
                  0 0 ${30 * glowPulse * scale}px rgba(0, 255, 136, ${0.8 * glowPulse}),
                  0 0 ${60 * glowPulse * scale}px rgba(0, 255, 136, ${0.4 * glowPulse})
                `,
                letterSpacing: `-${2 * scale}px`,
              }}
            >
              87x
            </span>
            <span
              style={{
                fontSize: 48 * scale,
                fontWeight: 600,
                color: COLORS.success,
                marginLeft: 12 * scale,
                textShadow: `0 0 ${20 * glowPulse * scale}px rgba(0, 255, 136, ${0.6 * glowPulse})`,
              }}
            >
              faster
            </span>
          </div>

          {/* Additional sparkle particles around 87x */}
          {revealProgress > 0.5 &&
            [0, 1, 2, 3, 4, 5].map((i) => {
              const sparkleAngle = (i * 60 + pulseFrame * 2) % 360;
              const sparkleDistance = 150 + Math.sin(pulseFrame * 0.1 + i) * 20;
              const sparkleX = Math.cos((sparkleAngle * Math.PI) / 180) * sparkleDistance * scale;
              const sparkleY = Math.sin((sparkleAngle * Math.PI) / 180) * sparkleDistance * scale;
              const sparkleOpacity = 0.3 + Math.sin(pulseFrame * 0.15 + i) * 0.3;

              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    right: -sparkleX + 120 * scale,
                    top: "50%",
                    marginTop: sparkleY - 4 * scale,
                    width: 8 * scale,
                    height: 8 * scale,
                    borderRadius: "50%",
                    backgroundColor: COLORS.success,
                    opacity: sparkleOpacity,
                    boxShadow: `0 0 ${10 * scale}px ${COLORS.success}`,
                  }}
                />
              );
            })}
        </div>
      )}

      {/* Dramatic background glow when fast mode activates */}
      {showFastBar && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            pointerEvents: "none",
            background: `radial-gradient(ellipse at center, ${COLORS.success}08 0%, transparent 60%)`,
            opacity: fastBarGlow * 0.5,
          }}
        />
      )}
    </AbsoluteFill>
  );
};

export default HookScene;
