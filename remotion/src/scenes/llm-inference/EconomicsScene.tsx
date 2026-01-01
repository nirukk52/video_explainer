/**
 * Scene 16: The Economics of Scale
 *
 * Key insight: Real numbers show how expensive inference is,
 * and why every optimization matters.
 *
 * Visual flow:
 * 1. 1M users calculation
 * 2. GPU requirements
 * 3. Monthly cost
 * 4. Impact of 2x throughput improvement
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

interface EconomicsSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  money: "#2ecc71",
  cost: "#ff6b35",
  savings: "#00ff88",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
};

export const EconomicsScene: React.FC<EconomicsSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings
  const phase1End = Math.round(durationInFrames * 0.20); // Requirements calculation
  const phase2End = Math.round(durationInFrames * 0.47); // Cost reveal
  const phase3End = Math.round(durationInFrames * 0.73); // Optimization impact
  const phase4End = Math.round(durationInFrames * 1.00); // Final insight

  // Animated counters
  const usersCounter = interpolate(
    localFrame,
    [Math.round(durationInFrames * 0.03), Math.round(durationInFrames * 0.10)],
    [0, 1000000],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const tokensCounter = interpolate(
    localFrame,
    [Math.round(durationInFrames * 0.07), Math.round(durationInFrames * 0.13)],
    [0, 50000000],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const gpusCounter = interpolate(
    localFrame,
    [phase1End, phase1End + Math.round(durationInFrames * 0.07)],
    [0, 25000],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const costCounter = interpolate(
    localFrame,
    [phase1End + Math.round(durationInFrames * 0.07), phase2End],
    [0, 36],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Animations
  const introOpacity = interpolate(localFrame, [0, Math.round(durationInFrames * 0.02)], [0, 1], {
    extrapolateRight: "clamp",
  });

  const optimizationOpacity = interpolate(
    localFrame,
    [phase2End, phase2End + Math.round(durationInFrames * 0.03)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: introOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>17</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40 * scale,
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
          }}
        >
          The Economics of Scale
        </h1>
      </div>

      {/* Main content */}
      <div
        style={{
          position: "absolute",
          top: 120 * scale,
          left: 80 * scale,
          right: 80 * scale,
          opacity: introOpacity,
        }}
      >
        {/* Calculation chain */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 20 * scale,
            marginBottom: 40 * scale,
            flexWrap: "wrap",
          }}
        >
          {/* Users */}
          <div
            style={{
              padding: 20 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 12 * scale,
              border: `2px solid ${COLORS.primary}`,
              textAlign: "center",
              minWidth: 160 * scale,
            }}
          >
            <div
              style={{
                fontSize: 32 * scale,
                fontWeight: 700,
                fontFamily: "JetBrains Mono",
                color: COLORS.primary,
              }}
            >
              {Math.round(usersCounter).toLocaleString()}
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
              Concurrent Users
            </div>
          </div>

          <div style={{ fontSize: 24 * scale, color: COLORS.textDim }}>×</div>

          {/* Tokens per user */}
          <div
            style={{
              padding: 20 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 12 * scale,
              border: "1px solid #333",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 32 * scale,
                fontWeight: 700,
                fontFamily: "JetBrains Mono",
                color: COLORS.text,
              }}
            >
              50
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
              tokens/sec each
            </div>
          </div>

          <div style={{ fontSize: 24 * scale, color: COLORS.textDim }}>=</div>

          {/* Total throughput */}
          <div
            style={{
              padding: 20 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 12 * scale,
              border: `2px solid ${COLORS.cost}`,
              textAlign: "center",
              minWidth: 180 * scale,
            }}
          >
            <div
              style={{
                fontSize: 32 * scale,
                fontWeight: 700,
                fontFamily: "JetBrains Mono",
                color: COLORS.cost,
              }}
            >
              {Math.round(tokensCounter / 1000000)}M
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
              tokens/sec total
            </div>
          </div>
        </div>

        {/* GPU and Cost calculation */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 40 * scale,
            marginBottom: 40 * scale,
            opacity: interpolate(
              localFrame,
              [phase1End, phase1End + Math.round(durationInFrames * 0.02)],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          {/* GPU requirement */}
          <div
            style={{
              padding: 24 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              border: "1px solid #333",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 16 * scale, color: COLORS.textDim, marginBottom: 8 * scale }}>
              At 2,000 tok/s per GPU
            </div>
            <div
              style={{
                fontSize: 48 * scale,
                fontWeight: 700,
                fontFamily: "JetBrains Mono",
                color: COLORS.cost,
              }}
            >
              {Math.round(gpusCounter).toLocaleString()}
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.text }}>GPUs Required</div>
          </div>

          {/* Monthly cost */}
          <div
            style={{
              padding: 24 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 16 * scale,
              border: `2px solid ${COLORS.cost}`,
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 16 * scale, color: COLORS.textDim, marginBottom: 8 * scale }}>
              At $2/GPU-hour
            </div>
            <div
              style={{
                fontSize: 48 * scale,
                fontWeight: 700,
                fontFamily: "JetBrains Mono",
                color: COLORS.cost,
              }}
            >
              ${Math.round(costCounter)}M
            </div>
            <div style={{ fontSize: 18 * scale, color: COLORS.text }}>Per Month</div>
          </div>
        </div>

        {/* Optimization impact */}
        <div
          style={{
            padding: 24 * scale,
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            border: `2px solid ${COLORS.savings}`,
            opacity: optimizationOpacity,
          }}
        >
          <div
            style={{
              fontSize: 20 * scale,
              color: COLORS.text,
              marginBottom: 20 * scale,
              textAlign: "center",
            }}
          >
            Impact of 2× Throughput Improvement
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: 40 * scale,
            }}
          >
            {/* Before */}
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18 * scale, color: COLORS.textDim, marginBottom: 8 * scale }}>
                Before
              </div>
              <div
                style={{
                  fontSize: 36 * scale,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  color: COLORS.cost,
                }}
              >
                $36M/mo
              </div>
              <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
                25,000 GPUs
              </div>
            </div>

            {/* Arrow */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4 * scale,
              }}
            >
              <div
                style={{
                  padding: `${8 * scale}px ${16 * scale}px`,
                  backgroundColor: COLORS.savings + "20",
                  borderRadius: 8 * scale,
                  fontSize: 18 * scale,
                  fontWeight: 700,
                  color: COLORS.savings,
                }}
              >
                2× faster
              </div>
              <div style={{ fontSize: 24 * scale, color: COLORS.savings }}>→</div>
            </div>

            {/* After */}
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18 * scale, color: COLORS.textDim, marginBottom: 8 * scale }}>
                After
              </div>
              <div
                style={{
                  fontSize: 36 * scale,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  color: COLORS.savings,
                }}
              >
                $18M/mo
              </div>
              <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
                12,500 GPUs
              </div>
            </div>

            {/* Savings */}
            <div
              style={{
                padding: 16 * scale,
                backgroundColor: COLORS.savings + "15",
                borderRadius: 12 * scale,
                border: `2px solid ${COLORS.savings}`,
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: 28 * scale,
                  fontWeight: 700,
                  color: COLORS.savings,
                }}
              >
                $18M
              </div>
              <div style={{ fontSize: 18 * scale, color: COLORS.savings }}>
                Monthly Savings
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key insight */}
      <div
        style={{
          position: "absolute",
          bottom: 60 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: interpolate(
            localFrame,
            [phase3End, phase4End],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
        }}
      >
        <span style={{ fontSize: 22 * scale, color: COLORS.text }}>
          Every optimization in this video{" "}
          <span style={{ color: COLORS.savings, fontWeight: 700 }}>
            directly reduces your infrastructure bill
          </span>
        </span>
      </div>
    </AbsoluteFill>
  );
};

export default EconomicsScene;
