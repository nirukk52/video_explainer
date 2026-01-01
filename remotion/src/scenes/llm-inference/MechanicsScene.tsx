/**
 * Scene 9: How Attention Uses the Cache (Simplified)
 *
 * Clean visualization showing:
 * - The attention formula
 * - New token generates Q, cache provides K & V
 * - Visual flow of the computation
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

interface MechanicsSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  query: "#00d9ff",
  key: "#ff6b35",
  value: "#00ff88",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
  success: "#2ecc71",
};

export const MechanicsScene: React.FC<MechanicsSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const scale = Math.min(width / 1920, height / 1080);
  const localFrame = frame - startFrame;

  // Simple phase timings
  const phase1End = Math.round(durationInFrames * 0.35); // Show formula and new token
  const phase2End = Math.round(durationInFrames * 0.70); // Show cache usage
  const phase3End = durationInFrames; // Show output

  // Title fade in
  const titleOpacity = interpolate(localFrame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  // Formula appears
  const formulaOpacity = interpolate(localFrame, [15, 30], [0, 1], { extrapolateRight: "clamp" });

  // New token and Q generation
  const newTokenProgress = spring({
    frame: localFrame - 45,
    fps,
    config: { damping: 15, stiffness: 100 },
  });

  // Cache section appears
  const cacheProgress = interpolate(localFrame, [phase1End, phase1End + 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Output appears
  const outputProgress = interpolate(localFrame, [phase2End, phase2End + 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Arrow animation
  const arrowPulse = 0.5 + 0.5 * Math.sin((localFrame / fps) * Math.PI * 2);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: titleOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>10</span>
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
          How Attention Uses the Cache
        </h1>
      </div>

      {/* The Formula */}
      <div
        style={{
          position: "absolute",
          top: 140 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: formulaOpacity,
        }}
      >
        <div
          style={{
            display: "inline-block",
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            padding: `${20 * scale}px ${48 * scale}px`,
            border: `2px solid ${COLORS.text}30`,
          }}
        >
          <span
            style={{
              fontSize: 32 * scale,
              fontFamily: "JetBrains Mono, monospace",
              color: COLORS.text,
            }}
          >
            Attention = softmax(
            <span style={{ color: COLORS.query, fontWeight: 700 }}>Q</span>
            {" × "}
            <span style={{ color: COLORS.key, fontWeight: 700 }}>K</span>
            <sup>T</sup>
            ) ×{" "}
            <span style={{ color: COLORS.value, fontWeight: 700 }}>V</span>
          </span>
        </div>
      </div>

      {/* Main visualization - 3 columns layout */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex",
          alignItems: "center",
          gap: 60 * scale,
          marginTop: 40 * scale,
        }}
      >
        {/* Left: New Token generates Q */}
        <div
          style={{
            opacity: newTokenProgress,
            transform: `scale(${0.8 + 0.2 * newTokenProgress})`,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 20 * scale,
              color: COLORS.textDim,
              marginBottom: 16 * scale,
              fontWeight: 600,
            }}
          >
            New Token
          </div>
          <div
            style={{
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              padding: `${24 * scale}px ${32 * scale}px`,
              border: `3px solid ${COLORS.query}`,
              boxShadow: `0 0 30px ${COLORS.query}40`,
            }}
          >
            <div
              style={{
                fontSize: 36 * scale,
                fontWeight: 700,
                color: COLORS.query,
                marginBottom: 16 * scale,
              }}
            >
              "on"
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.textDim, marginBottom: 12 * scale }}>
              generates
            </div>
            <div
              style={{
                display: "inline-block",
                backgroundColor: COLORS.query + "30",
                borderRadius: 12 * scale,
                padding: `${16 * scale}px ${32 * scale}px`,
                border: `2px solid ${COLORS.query}`,
              }}
            >
              <span
                style={{
                  fontSize: 32 * scale,
                  fontWeight: 700,
                  color: COLORS.query,
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                Q
              </span>
              <span style={{ fontSize: 16 * scale, color: COLORS.query, marginLeft: 8 * scale }}>
                (Query)
              </span>
            </div>
          </div>
        </div>

        {/* Arrow */}
        <div
          style={{
            opacity: cacheProgress,
            fontSize: 48 * scale,
            color: COLORS.textDim,
          }}
        >
          →
        </div>

        {/* Center: Cache provides K & V */}
        <div
          style={{
            opacity: cacheProgress,
            transform: `scale(${0.8 + 0.2 * cacheProgress})`,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 20 * scale,
              color: COLORS.textDim,
              marginBottom: 16 * scale,
              fontWeight: 600,
            }}
          >
            KV Cache
          </div>
          <div
            style={{
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              padding: `${24 * scale}px ${40 * scale}px`,
              border: `3px solid #9b59b6`,
              boxShadow: `0 0 ${20 + arrowPulse * 10}px #9b59b640`,
            }}
          >
            <div style={{ fontSize: 18 * scale, color: COLORS.textDim, marginBottom: 16 * scale }}>
              provides all cached
            </div>
            <div style={{ display: "flex", gap: 24 * scale, justifyContent: "center" }}>
              {/* K column */}
              <div
                style={{
                  backgroundColor: COLORS.key + "20",
                  borderRadius: 12 * scale,
                  padding: `${16 * scale}px ${24 * scale}px`,
                  border: `2px solid ${COLORS.key}`,
                }}
              >
                <div
                  style={{
                    fontSize: 24 * scale,
                    fontWeight: 700,
                    color: COLORS.key,
                    fontFamily: "JetBrains Mono, monospace",
                    marginBottom: 12 * scale,
                  }}
                >
                  K
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 * scale }}>
                  {["K₁", "K₂", "K₃"].map((k, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: 18 * scale,
                        color: COLORS.key,
                        fontFamily: "JetBrains Mono, monospace",
                        backgroundColor: COLORS.key + "30",
                        padding: `${6 * scale}px ${12 * scale}px`,
                        borderRadius: 6 * scale,
                      }}
                    >
                      {k}
                    </div>
                  ))}
                </div>
              </div>

              {/* V column */}
              <div
                style={{
                  backgroundColor: COLORS.value + "20",
                  borderRadius: 12 * scale,
                  padding: `${16 * scale}px ${24 * scale}px`,
                  border: `2px solid ${COLORS.value}`,
                }}
              >
                <div
                  style={{
                    fontSize: 24 * scale,
                    fontWeight: 700,
                    color: COLORS.value,
                    fontFamily: "JetBrains Mono, monospace",
                    marginBottom: 12 * scale,
                  }}
                >
                  V
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 * scale }}>
                  {["V₁", "V₂", "V₃"].map((v, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: 18 * scale,
                        color: COLORS.value,
                        fontFamily: "JetBrains Mono, monospace",
                        backgroundColor: COLORS.value + "30",
                        padding: `${6 * scale}px ${12 * scale}px`,
                        borderRadius: 6 * scale,
                      }}
                    >
                      {v}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Arrow */}
        <div
          style={{
            opacity: outputProgress,
            fontSize: 48 * scale,
            color: COLORS.textDim,
          }}
        >
          →
        </div>

        {/* Right: Output */}
        <div
          style={{
            opacity: outputProgress,
            transform: `scale(${0.8 + 0.2 * outputProgress})`,
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 20 * scale,
              color: COLORS.textDim,
              marginBottom: 16 * scale,
              fontWeight: 600,
            }}
          >
            Result
          </div>
          <div
            style={{
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              padding: `${24 * scale}px ${32 * scale}px`,
              border: `3px solid ${COLORS.success}`,
              boxShadow: `0 0 30px ${COLORS.success}40`,
            }}
          >
            <div
              style={{
                fontSize: 18 * scale,
                color: COLORS.textDim,
                marginBottom: 16 * scale,
              }}
            >
              Attention output
            </div>
            <div
              style={{
                display: "flex",
                gap: 8 * scale,
                justifyContent: "center",
              }}
            >
              {[0.7, 0.5, 0.9, 0.6].map((h, i) => (
                <div
                  key={i}
                  style={{
                    width: 16 * scale,
                    height: 60 * h * outputProgress * scale,
                    background: `linear-gradient(to top, ${COLORS.value}, ${COLORS.query})`,
                    borderRadius: 4 * scale,
                  }}
                />
              ))}
            </div>
            <div style={{ fontSize: 16 * scale, color: COLORS.success, marginTop: 12 * scale }}>
              Mixed from all tokens
            </div>
          </div>
        </div>
      </div>

      {/* Key insight at bottom */}
      <div
        style={{
          position: "absolute",
          bottom: 80 * scale,
          left: "50%",
          transform: "translateX(-50%)",
          opacity: outputProgress,
        }}
      >
        <div
          style={{
            backgroundColor: COLORS.success + "15",
            border: `3px solid ${COLORS.success}`,
            borderRadius: 16 * scale,
            padding: `${20 * scale}px ${40 * scale}px`,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontSize: 26 * scale,
              color: COLORS.text,
            }}
          >
            Only <span style={{ color: COLORS.query, fontWeight: 700 }}>one Q</span> computed per token.
            All <span style={{ color: COLORS.key, fontWeight: 700 }}>K</span>s and{" "}
            <span style={{ color: COLORS.value, fontWeight: 700 }}>V</span>s from cache = massive savings!
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default MechanicsScene;
