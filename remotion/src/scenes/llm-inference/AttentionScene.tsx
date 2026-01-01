/**
 * Scene 4: Understanding Attention - Simplified for Technical Audience
 *
 * Focus: Set up the KV cache insight by showing that K and V
 * for past tokens don't change when generating new tokens.
 *
 * Visual flow:
 * 1. Show attention formula
 * 2. Show past tokens with their K,V pairs
 * 3. New token arrives, generates Q
 * 4. Q attends to all past K vectors
 * 5. Key insight: K,V for past tokens never change
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

interface AttentionSceneProps {
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
  attention: "#9b59b6",
  highlight: "#ffd700",
};

// Token component showing a word with its K,V vectors
const TokenWithKV: React.FC<{
  word: string;
  index: number;
  opacity: number;
  scale: number;
  showKV: boolean;
  isHighlighted?: boolean;
  attentionWeight?: number;
}> = ({ word, index, opacity, scale, showKV, isHighlighted = false, attentionWeight }) => {
  return (
    <div
      style={{
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8 * scale,
      }}
    >
      {/* Token word */}
      <div
        style={{
          padding: `${12 * scale}px ${20 * scale}px`,
          backgroundColor: isHighlighted ? `${COLORS.highlight}30` : COLORS.surface,
          borderRadius: 8 * scale,
          border: `2px solid ${isHighlighted ? COLORS.highlight : "#444"}`,
          fontSize: 24 * scale,
          fontWeight: 600,
          color: isHighlighted ? COLORS.highlight : COLORS.text,
          boxShadow: isHighlighted ? `0 0 ${20 * scale}px ${COLORS.highlight}40` : "none",
        }}
      >
        {word}
      </div>

      {/* K,V vectors */}
      {showKV && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4 * scale,
            alignItems: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6 * scale,
              padding: `${6 * scale}px ${12 * scale}px`,
              backgroundColor: `${COLORS.key}20`,
              borderRadius: 6 * scale,
              border: `1px solid ${COLORS.key}40`,
            }}
          >
            <span style={{ fontSize: 16 * scale, fontWeight: 700, color: COLORS.key }}>K</span>
            <span style={{ fontSize: 18 * scale, color: COLORS.key, opacity: 0.7 }}>_{index + 1}</span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6 * scale,
              padding: `${6 * scale}px ${12 * scale}px`,
              backgroundColor: `${COLORS.value}20`,
              borderRadius: 6 * scale,
              border: `1px solid ${COLORS.value}40`,
            }}
          >
            <span style={{ fontSize: 16 * scale, fontWeight: 700, color: COLORS.value }}>V</span>
            <span style={{ fontSize: 18 * scale, color: COLORS.value, opacity: 0.7 }}>_{index + 1}</span>
          </div>
        </div>
      )}

      {/* Attention weight indicator */}
      {attentionWeight !== undefined && attentionWeight > 0 && (
        <div
          style={{
            width: 60 * scale,
            height: 8 * scale,
            backgroundColor: `${COLORS.attention}30`,
            borderRadius: 4 * scale,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${attentionWeight * 100}%`,
              height: "100%",
              backgroundColor: COLORS.attention,
              borderRadius: 4 * scale,
            }}
          />
        </div>
      )}
    </div>
  );
};

// New token with Query vector
const NewTokenWithQ: React.FC<{
  opacity: number;
  scale: number;
  showQ: boolean;
}> = ({ opacity, scale, showQ }) => {
  return (
    <div
      style={{
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8 * scale,
      }}
    >
      {/* New token indicator */}
      <div
        style={{
          padding: `${12 * scale}px ${20 * scale}px`,
          backgroundColor: `${COLORS.query}20`,
          borderRadius: 8 * scale,
          border: `2px solid ${COLORS.query}`,
          fontSize: 24 * scale,
          fontWeight: 600,
          color: COLORS.query,
          boxShadow: `0 0 ${20 * scale}px ${COLORS.query}40`,
        }}
      >
        ???
      </div>

      {/* Q vector */}
      {showQ && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6 * scale,
            padding: `${8 * scale}px ${16 * scale}px`,
            backgroundColor: `${COLORS.query}30`,
            borderRadius: 6 * scale,
            border: `2px solid ${COLORS.query}`,
          }}
        >
          <span style={{ fontSize: 20 * scale, fontWeight: 700, color: COLORS.query }}>Q</span>
          <span style={{ fontSize: 16 * scale, color: COLORS.query, opacity: 0.7 }}>new</span>
        </div>
      )}
    </div>
  );
};

// Attention arrow from Q to K
const AttentionArrow: React.FC<{
  opacity: number;
  scale: number;
  fromX: number;
  toX: number;
  y: number;
}> = ({ opacity, scale, fromX, toX, y }) => {
  return (
    <svg
      style={{
        position: "absolute",
        top: y,
        left: 0,
        width: "100%",
        height: 60 * scale,
        opacity,
        pointerEvents: "none",
      }}
    >
      <defs>
        <marker
          id="attention-arrow"
          markerWidth={10}
          markerHeight={7}
          refX={9}
          refY={3.5}
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill={COLORS.attention} />
        </marker>
      </defs>
      <path
        d={`M ${fromX} ${30 * scale} Q ${(fromX + toX) / 2} ${-10 * scale} ${toX} ${30 * scale}`}
        stroke={COLORS.attention}
        strokeWidth={2 * scale}
        fill="none"
        markerEnd="url(#attention-arrow)"
        strokeDasharray={`${5 * scale} ${3 * scale}`}
      />
    </svg>
  );
};

export const AttentionScene: React.FC<AttentionSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings - 4 phases for simplified flow
  const phase1End = Math.round(durationInFrames * 0.25); // Show formula + past tokens
  const phase2End = Math.round(durationInFrames * 0.50); // Show K,V for each token
  const phase3End = Math.round(durationInFrames * 0.75); // New token with Q, attention
  const phase4End = Math.round(durationInFrames * 1.00); // Key insight

  const tokens = ["The", "cat", "sat", "on", "the"];

  // Animations
  const titleOpacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  const formulaOpacity = interpolate(localFrame, [15, 45], [0, 1], {
    extrapolateRight: "clamp",
  });

  const tokensOpacity = interpolate(localFrame, [30, 60], [0, 1], {
    extrapolateRight: "clamp",
  });

  const kvOpacity = interpolate(
    localFrame,
    [phase1End, phase1End + 30],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const newTokenOpacity = interpolate(
    localFrame,
    [phase2End, phase2End + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const qOpacity = interpolate(
    localFrame,
    [phase2End + 20, phase2End + 40],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const attentionOpacity = interpolate(
    localFrame,
    [phase2End + 40, phase3End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const insightOpacity = interpolate(
    localFrame,
    [phase3End, phase3End + 30],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Attention weights for visualization
  const attentionWeights = [0.15, 0.35, 0.20, 0.10, 0.20];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: titleOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>4</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
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
          Attention Refresher
        </h1>
      </div>

      {/* Attention formula */}
      <div
        style={{
          position: "absolute",
          top: 110 * scale,
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
            padding: `${16 * scale}px ${32 * scale}px`,
            borderRadius: 12 * scale,
            border: `1px solid ${COLORS.attention}40`,
          }}
        >
          <span
            style={{
              fontSize: 28 * scale,
              fontFamily: "JetBrains Mono, monospace",
              color: COLORS.text,
            }}
          >
            Attention = softmax(
            <span style={{ color: COLORS.query }}>Q</span>
            <span style={{ color: COLORS.key }}>K</span>
            <sup style={{ fontSize: 18 * scale }}>T</sup> / √d
            <sub style={{ fontSize: 16 * scale }}>k</sub>)
            <span style={{ color: COLORS.value }}>V</span>
          </span>
        </div>
      </div>

      {/* Main content - tokens with K,V */}
      <div
        style={{
          position: "absolute",
          top: 220 * scale,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        {/* Label for past tokens */}
        <div
          style={{
            opacity: tokensOpacity,
            marginBottom: 20 * scale,
            fontSize: 20 * scale,
            color: COLORS.textDim,
          }}
        >
          Past tokens (already processed)
        </div>

        {/* Tokens row */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 24 * scale,
            marginBottom: 40 * scale,
          }}
        >
          {tokens.map((word, idx) => (
            <TokenWithKV
              key={idx}
              word={word}
              index={idx}
              opacity={tokensOpacity}
              scale={scale}
              showKV={kvOpacity > 0}
              attentionWeight={attentionOpacity > 0 ? attentionWeights[idx] * attentionOpacity : undefined}
            />
          ))}

          {/* Arrow to new token */}
          {newTokenOpacity > 0 && (
            <div
              style={{
                opacity: newTokenOpacity,
                display: "flex",
                alignItems: "center",
                fontSize: 32 * scale,
                color: COLORS.textDim,
                marginTop: 10 * scale,
              }}
            >
              →
            </div>
          )}

          {/* New token */}
          <NewTokenWithQ
            opacity={newTokenOpacity}
            scale={scale}
            showQ={qOpacity > 0}
          />
        </div>

        {/* Attention flow explanation */}
        {attentionOpacity > 0 && (
          <div
            style={{
              opacity: attentionOpacity,
              display: "flex",
              alignItems: "center",
              gap: 16 * scale,
              padding: `${16 * scale}px ${32 * scale}px`,
              backgroundColor: `${COLORS.attention}15`,
              borderRadius: 12 * scale,
              border: `2px solid ${COLORS.attention}40`,
              marginBottom: 30 * scale,
            }}
          >
            <span style={{ fontSize: 22 * scale, color: COLORS.query, fontWeight: 600 }}>Q</span>
            <span style={{ fontSize: 20 * scale, color: COLORS.textDim }}>attends to all</span>
            <span style={{ fontSize: 22 * scale, color: COLORS.key, fontWeight: 600 }}>K</span>
            <span style={{ fontSize: 20 * scale, color: COLORS.textDim }}>→ weights →</span>
            <span style={{ fontSize: 20 * scale, color: COLORS.textDim }}>weighted sum of</span>
            <span style={{ fontSize: 22 * scale, color: COLORS.value, fontWeight: 600 }}>V</span>
          </div>
        )}

        {/* Key insight */}
        {insightOpacity > 0 && (
          <div
            style={{
              opacity: insightOpacity,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 16 * scale,
            }}
          >
            <div
              style={{
                padding: `${20 * scale}px ${40 * scale}px`,
                backgroundColor: `${COLORS.highlight}15`,
                borderRadius: 12 * scale,
                border: `2px solid ${COLORS.highlight}`,
                boxShadow: `0 0 ${30 * scale}px ${COLORS.highlight}30`,
              }}
            >
              <span style={{ fontSize: 26 * scale, color: COLORS.highlight, fontWeight: 600 }}>
                Key insight: <span style={{ color: COLORS.key }}>K</span> and{" "}
                <span style={{ color: COLORS.value }}>V</span> for past tokens{" "}
                <span style={{ color: COLORS.text }}>never change</span>
              </span>
            </div>

            <div style={{ fontSize: 22 * scale, color: COLORS.textDim }}>
              So why recompute them every time?
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          bottom: 40 * scale,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 40 * scale,
          opacity: kvOpacity,
        }}
      >
        {[
          { label: "Query", color: COLORS.query, desc: "What to look for" },
          { label: "Key", color: COLORS.key, desc: "What each token offers" },
          { label: "Value", color: COLORS.value, desc: "The actual content" },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12 * scale,
            }}
          >
            <div
              style={{
                width: 16 * scale,
                height: 16 * scale,
                backgroundColor: item.color,
                borderRadius: 4 * scale,
              }}
            />
            <span style={{ fontSize: 16 * scale, color: item.color, fontWeight: 600 }}>
              {item.label}
            </span>
            <span style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
              {item.desc}
            </span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export default AttentionScene;
