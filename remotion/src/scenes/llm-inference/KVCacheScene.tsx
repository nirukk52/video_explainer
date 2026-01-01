/**
 * Scene 8: The KV Cache Solution (Simplified)
 *
 * Clean visualization showing how KV cache works:
 * - Simple token sequence with K/V generation
 * - Horizontal cache that grows
 * - Clear reuse visualization
 * - Before/after comparison
 */

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";
import { COLORS as STYLE_COLORS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface KVCacheSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  key: "#ff6b35",
  value: "#00ff88",
  cache: "#9b59b6",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
  success: "#2ecc71",
  error: "#e74c3c",
};

const TOKENS = ["The", "cat", "sat"];

export const KVCacheScene: React.FC<KVCacheSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Simple phase timings
  const phase1End = Math.round(durationInFrames * 0.30); // Show tokens 1-3 being cached
  const phase2Start = phase1End;
  const phase2End = Math.round(durationInFrames * 0.60); // Show reuse concept
  const phase3Start = phase2End;
  const phase3End = durationInFrames; // Show savings

  // Title opacity
  const titleOpacity = interpolate(localFrame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  // How many tokens are visible (0-3)
  const visibleTokens = Math.min(
    3,
    Math.floor(interpolate(localFrame, [30, phase1End], [0, 3], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }))
  );

  // Reuse phase progress
  const reuseProgress = interpolate(
    localFrame,
    [phase2Start, phase2Start + 60],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Savings phase progress
  const savingsProgress = interpolate(
    localFrame,
    [phase3Start, phase3Start + 60],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Current step text
  const getStepText = () => {
    if (localFrame < 30) return "Each token needs Key and Value vectors for attention";
    if (localFrame < phase1End) return `Processing token ${visibleTokens}... computing K and V`;
    if (localFrame < phase2End) return "With KV Cache: Reuse previous K/V pairs!";
    return "Result: Only compute new token's K/V each step";
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: titleOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>9</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 50 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
        }}
      >
        <h1
          style={{
            fontSize: 56 * scale,
            fontWeight: 700,
            color: STYLE_COLORS.primary,
            margin: 0,
          }}
        >
          The KV Cache Solution
        </h1>
      </div>

      {/* Step indicator */}
      <div
        style={{
          position: "absolute",
          top: 130 * scale,
          left: "50%",
          transform: "translateX(-50%)",
          opacity: interpolate(localFrame, [15, 30], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        <div
          style={{
            padding: `${16 * scale}px ${32 * scale}px`,
            backgroundColor: COLORS.surface,
            borderRadius: 12 * scale,
            border: `2px solid ${COLORS.primary}40`,
          }}
        >
          <span
            style={{
              fontSize: 24 * scale,
              color: COLORS.text,
              fontWeight: 500,
            }}
          >
            {getStepText()}
          </span>
        </div>
      </div>

      {/* Main visualization area */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 1200 * scale,
        }}
      >
        {/* Token sequence with K/V boxes */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 60 * scale,
            marginBottom: 60 * scale,
          }}
        >
          {TOKENS.map((token, i) => {
            const isVisible = i < visibleTokens;
            const isReused = localFrame >= phase2Start && i < visibleTokens - 1;

            const tokenOpacity = isVisible
              ? spring({
                  frame: localFrame - 30 - i * 30,
                  fps,
                  config: { damping: 15, stiffness: 100 },
                })
              : 0;

            const glowPulse = isReused ? 0.5 + 0.5 * Math.sin((localFrame / fps) * Math.PI * 2) : 0;

            return (
              <div
                key={i}
                style={{
                  opacity: tokenOpacity,
                  transform: `scale(${tokenOpacity})`,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 16 * scale,
                }}
              >
                {/* Token label */}
                <div
                  style={{
                    fontSize: 18 * scale,
                    color: COLORS.textDim,
                    fontWeight: 600,
                  }}
                >
                  Token {i + 1}
                </div>

                {/* Token text */}
                <div
                  style={{
                    fontSize: 32 * scale,
                    fontWeight: 700,
                    color: COLORS.primary,
                    padding: `${16 * scale}px ${24 * scale}px`,
                    backgroundColor: COLORS.surface,
                    borderRadius: 12 * scale,
                    border: `3px solid ${COLORS.primary}`,
                  }}
                >
                  "{token}"
                </div>

                {/* Arrow down */}
                <div
                  style={{
                    fontSize: 28 * scale,
                    color: COLORS.textDim,
                  }}
                >
                  ↓
                </div>

                {/* K/V pair */}
                <div
                  style={{
                    display: "flex",
                    gap: 12 * scale,
                  }}
                >
                  <div
                    style={{
                      width: 70 * scale,
                      height: 50 * scale,
                      backgroundColor: COLORS.key,
                      borderRadius: 8 * scale,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 22 * scale,
                      fontWeight: 700,
                      color: "#000",
                      fontFamily: "JetBrains Mono, monospace",
                      boxShadow: isReused
                        ? `0 0 ${20 + glowPulse * 15}px ${COLORS.key}`
                        : `0 0 10px ${COLORS.key}40`,
                    }}
                  >
                    K{i + 1}
                  </div>
                  <div
                    style={{
                      width: 70 * scale,
                      height: 50 * scale,
                      backgroundColor: COLORS.value,
                      borderRadius: 8 * scale,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 22 * scale,
                      fontWeight: 700,
                      color: "#000",
                      fontFamily: "JetBrains Mono, monospace",
                      boxShadow: isReused
                        ? `0 0 ${20 + glowPulse * 15}px ${COLORS.value}`
                        : `0 0 10px ${COLORS.value}40`,
                    }}
                  >
                    V{i + 1}
                  </div>
                </div>

                {/* Reused badge */}
                {isReused && (
                  <div
                    style={{
                      marginTop: 8 * scale,
                      padding: `${6 * scale}px ${16 * scale}px`,
                      backgroundColor: COLORS.primary + "30",
                      borderRadius: 20 * scale,
                      border: `2px solid ${COLORS.primary}`,
                      opacity: reuseProgress,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 14 * scale,
                        fontWeight: 700,
                        color: COLORS.primary,
                      }}
                    >
                      ✓ CACHED & REUSED
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Cache storage visualization */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            opacity: visibleTokens > 0 ? 1 : 0,
          }}
        >
          <div
            style={{
              padding: `${24 * scale}px ${48 * scale}px`,
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              border: `3px solid ${COLORS.cache}`,
              boxShadow: `0 0 30px ${COLORS.cache}40`,
            }}
          >
            <div
              style={{
                fontSize: 20 * scale,
                color: COLORS.cache,
                fontWeight: 700,
                marginBottom: 16 * scale,
                textAlign: "center",
              }}
            >
              📦 KV CACHE
            </div>
            <div
              style={{
                display: "flex",
                gap: 20 * scale,
                justifyContent: "center",
              }}
            >
              {TOKENS.slice(0, visibleTokens).map((_, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: 8 * scale,
                    padding: `${12 * scale}px ${16 * scale}px`,
                    backgroundColor: COLORS.cache + "20",
                    borderRadius: 8 * scale,
                    border: `2px solid ${COLORS.cache}60`,
                  }}
                >
                  <span style={{ color: COLORS.key, fontWeight: 700, fontSize: 18 * scale }}>
                    K{i + 1}
                  </span>
                  <span style={{ color: COLORS.value, fontWeight: 700, fontSize: 18 * scale }}>
                    V{i + 1}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Key insight at bottom */}
      {savingsProgress > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: 80 * scale,
            left: "50%",
            transform: `translateX(-50%) scale(${0.8 + savingsProgress * 0.2})`,
            opacity: savingsProgress,
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 40 * scale,
              alignItems: "center",
            }}
          >
            {/* Without cache */}
            <div
              style={{
                padding: `${20 * scale}px ${32 * scale}px`,
                backgroundColor: COLORS.error + "20",
                borderRadius: 12 * scale,
                border: `3px solid ${COLORS.error}`,
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.error, fontWeight: 700, marginBottom: 8 * scale }}>
                ❌ Without Cache
              </div>
              <div style={{ fontSize: 28 * scale, color: COLORS.error, fontWeight: 800 }}>
                6 computations
              </div>
            </div>

            <div style={{ fontSize: 32 * scale, color: COLORS.textDim }}>→</div>

            {/* With cache */}
            <div
              style={{
                padding: `${20 * scale}px ${32 * scale}px`,
                backgroundColor: COLORS.success + "20",
                borderRadius: 12 * scale,
                border: `3px solid ${COLORS.success}`,
                textAlign: "center",
                boxShadow: `0 0 30px ${COLORS.success}40`,
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.success, fontWeight: 700, marginBottom: 8 * scale }}>
                ✅ With KV Cache
              </div>
              <div style={{ fontSize: 28 * scale, color: COLORS.success, fontWeight: 800 }}>
                3 computations
              </div>
            </div>

            <div style={{ fontSize: 32 * scale, color: COLORS.textDim }}>=</div>

            {/* Savings */}
            <div
              style={{
                padding: `${20 * scale}px ${32 * scale}px`,
                backgroundColor: COLORS.primary + "20",
                borderRadius: 12 * scale,
                border: `3px solid ${COLORS.primary}`,
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.primary, fontWeight: 700, marginBottom: 8 * scale }}>
                🚀 Savings
              </div>
              <div style={{ fontSize: 28 * scale, color: COLORS.primary, fontWeight: 800 }}>
                50% less work!
              </div>
            </div>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export default KVCacheScene;
