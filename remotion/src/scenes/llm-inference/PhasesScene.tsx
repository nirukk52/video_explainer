/**
 * Scene 2: The Two Phases
 *
 * Key insight: LLM inference has two distinct phases with different characteristics
 * - Prefill: Process ALL input tokens in parallel (compute-bound)
 * - Decode: Generate output tokens one-by-one (memory-bound)
 *
 * Visual flow:
 * 1. Show input prompt tokens
 * 2. PREFILL: All tokens light up simultaneously
 * 3. Show GPU utilization at 100%
 * 4. Transition to decode
 * 5. DECODE: Tokens appear one at a time
 * 6. Show GPU waiting
 */

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS as STYLE_COLORS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface PhasesSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  prefill: "#00d9ff", // Cyan for prefill/compute
  decode: "#ff6b35", // Orange for decode/memory
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
  active: "#00ff88",
};

const INPUT_TOKENS = ["What", "is", "the", "capital", "of", "France", "?"];
const OUTPUT_TOKENS = ["The", "capital", "of", "France", "is", "Paris", "."];

export const PhasesScene: React.FC<PhasesSceneProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Responsive scaling based on 1920x1080 reference
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings - proportional to total scene duration
  const phase1End = Math.round(durationInFrames * 0.15); // Show input tokens (~15%)
  const phase2End = Math.round(durationInFrames * 0.35); // Prefill animation (~35%)
  const phase3End = Math.round(durationInFrames * 0.50); // Transition (~50%)
  const phase4End = Math.round(durationInFrames * 0.90); // Decode animation (~90%)
  const phase5End = Math.round(durationInFrames * 1.00); // Summary (100%)

  // Prefill animation - all tokens light up at once
  const prefillProgress = interpolate(
    localFrame,
    [phase1End, phase1End + Math.round(durationInFrames * 0.025)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // GPU utilization during prefill (90% realistic max - not quite 100%)
  const prefillGPU = interpolate(
    localFrame,
    [phase1End, phase1End + Math.round(durationInFrames * 0.05)],
    [10, 90],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Decode animation - tokens appear one by one
  const decodeStartFrame = phase3End;
  const tokensPerSecond = 1.5; // Slower for visibility
  const decodeTokenCount = Math.min(
    OUTPUT_TOKENS.length,
    Math.floor(
      interpolate(
        localFrame,
        [decodeStartFrame, phase4End],
        [0, OUTPUT_TOKENS.length],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      )
    )
  );

  // GPU utilization during decode (drops significantly from 90% to 15%)
  const decodeGPU = interpolate(
    localFrame,
    [phase3End, phase3End + Math.round(durationInFrames * 0.05)],
    [90, 15],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Current phase
  const inPrefill = localFrame >= phase1End && localFrame < phase3End;
  const inDecode = localFrame >= phase3End;
  const currentGPU = inDecode ? decodeGPU : inPrefill ? prefillGPU : 10;

  // Phase labels
  const showPrefillLabel = localFrame > phase1End;
  const showDecodeLabel = localFrame > phase3End;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: interpolate(localFrame, [0, Math.round(durationInFrames * 0.025)], [0, 1]) }}>
        <span style={getSceneIndicatorTextStyle(scale)}>2</span>
      </div>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 40 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: interpolate(localFrame, [0, Math.round(durationInFrames * 0.025)], [0, 1]),
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
          The Two Phases of Inference
        </h1>
      </div>

      {/* Split view container */}
      <div
        style={{
          position: "absolute",
          top: 120 * scale,
          left: 60 * scale,
          right: 60 * scale,
          bottom: 150 * scale,
          display: "flex",
          gap: 40 * scale,
        }}
      >
        {/* PREFILL SIDE */}
        <div
          style={{
            flex: 1,
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            padding: 24 * scale,
            border: `${2 * scale}px solid ${inPrefill ? COLORS.prefill : "#333"}`,
            opacity: interpolate(localFrame, [0, Math.round(durationInFrames * 0.05)], [0, 1]),
            transition: "border-color 0.3s",
          }}
        >
          {/* Prefill header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 24 * scale,
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 28 * scale,
                  fontWeight: 700,
                  color: COLORS.prefill,
                }}
              >
                PREFILL
              </div>
              <div
                style={{
                  fontSize: 16 * scale,
                  color: COLORS.textDim,
                  marginTop: 4 * scale,
                }}
              >
                Process input tokens
              </div>
            </div>
            <div
              style={{
                padding: `${8 * scale}px ${16 * scale}px`,
                backgroundColor: COLORS.prefill + "20",
                borderRadius: 8 * scale,
                fontSize: 16 * scale,
                color: COLORS.prefill,
                fontWeight: 600,
                opacity: showPrefillLabel ? 1 : 0,
              }}
            >
              PARALLEL
            </div>
          </div>

          {/* Input tokens with parallel processing visualization */}
          <div style={{ position: "relative" }}>
            {/* Parallel processing indicator - all tokens connected */}
            {prefillProgress > 0 && (
              <div
                style={{
                  position: "absolute",
                  top: -30 * scale,
                  left: 0,
                  right: 0,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: 8 * scale,
                }}
              >
                <div
                  style={{
                    height: 2 * scale,
                    flex: 1,
                    background: `linear-gradient(90deg, transparent, ${COLORS.prefill}, transparent)`,
                    opacity: 0.8,
                  }}
                />
                <span
                  style={{
                    fontSize: 18 * scale,
                    color: COLORS.prefill,
                    fontWeight: 600,
                    whiteSpace: "nowrap",
                  }}
                >
                  ALL AT ONCE
                </span>
                <div
                  style={{
                    height: 2 * scale,
                    flex: 1,
                    background: `linear-gradient(90deg, transparent, ${COLORS.prefill}, transparent)`,
                    opacity: 0.8,
                  }}
                />
              </div>
            )}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 12 * scale,
                marginBottom: 32 * scale,
                marginTop: prefillProgress > 0 ? 8 * scale : 0,
              }}
            >
              {INPUT_TOKENS.map((token, i) => {
                const isActive = prefillProgress > 0;
                // Pulsing effect to show parallel processing
                const pulseOffset = Math.sin(localFrame * 0.15) * 0.1;
                return (
                  <div
                    key={i}
                    style={{
                      padding: `${12 * scale}px ${20 * scale}px`,
                      backgroundColor: isActive
                        ? COLORS.prefill + "30"
                        : COLORS.surface,
                      border: `${2 * scale}px solid ${isActive ? COLORS.prefill : "#444"}`,
                      borderRadius: 8 * scale,
                      fontSize: 18 * scale,
                      fontWeight: 500,
                      color: isActive ? COLORS.prefill : COLORS.text,
                      transform: isActive ? `scale(${1.05 + pulseOffset})` : "scale(1)",
                      transition: "all 0.2s",
                      boxShadow: isActive
                        ? `0 0 ${20 * scale}px ${COLORS.prefill}60, 0 0 ${40 * scale}px ${COLORS.prefill}30`
                        : "none",
                    }}
                  >
                    {token}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Prefill description */}
          <div
            style={{
              fontSize: 16 * scale,
              color: COLORS.textDim,
              lineHeight: 1.6,
              opacity: showPrefillLabel ? 1 : 0,
            }}
          >
            All {INPUT_TOKENS.length} tokens processed{" "}
            <span style={{ color: COLORS.prefill, fontWeight: 600 }}>
              simultaneously
            </span>{" "}
            in one forward pass. GPU tensor cores at full utilization.
          </div>
        </div>

        {/* DECODE SIDE */}
        <div
          style={{
            flex: 1,
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            padding: 24 * scale,
            border: `${2 * scale}px solid ${inDecode ? COLORS.decode : "#333"}`,
            opacity: interpolate(localFrame, [phase2End, phase3End], [0.5, 1]),
            transition: "border-color 0.3s",
          }}
        >
          {/* Decode header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 24 * scale,
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 28 * scale,
                  fontWeight: 700,
                  color: COLORS.decode,
                }}
              >
                DECODE
              </div>
              <div
                style={{
                  fontSize: 16 * scale,
                  color: COLORS.textDim,
                  marginTop: 4 * scale,
                }}
              >
                Generate output tokens
              </div>
            </div>
            <div
              style={{
                padding: `${8 * scale}px ${16 * scale}px`,
                backgroundColor: COLORS.decode + "20",
                borderRadius: 8 * scale,
                fontSize: 16 * scale,
                color: COLORS.decode,
                fontWeight: 600,
                opacity: showDecodeLabel ? 1 : 0,
              }}
            >
              SEQUENTIAL
            </div>
          </div>

          {/* Output tokens */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12 * scale,
              marginBottom: 32 * scale,
              minHeight: 100 * scale,
            }}
          >
            {OUTPUT_TOKENS.slice(0, decodeTokenCount).map((token, i) => {
              const isLatest = i === decodeTokenCount - 1;
              return (
                <div
                  key={i}
                  style={{
                    padding: `${12 * scale}px ${20 * scale}px`,
                    backgroundColor: isLatest
                      ? COLORS.decode + "30"
                      : COLORS.active + "20",
                    border: `${2 * scale}px solid ${isLatest ? COLORS.decode : COLORS.active}`,
                    borderRadius: 8 * scale,
                    fontSize: 18 * scale,
                    fontWeight: 500,
                    color: isLatest ? COLORS.decode : COLORS.active,
                    boxShadow: isLatest
                      ? `0 0 ${20 * scale}px ${COLORS.decode}40`
                      : "none",
                  }}
                >
                  {token}
                </div>
              );
            })}
            {decodeTokenCount < OUTPUT_TOKENS.length && inDecode && (
              <div
                style={{
                  padding: `${12 * scale}px ${20 * scale}px`,
                  backgroundColor: "transparent",
                  border: `${2 * scale}px dashed #444`,
                  borderRadius: 8 * scale,
                  fontSize: 18 * scale,
                  color: COLORS.textDim,
                  opacity: Math.sin(localFrame * 0.2) > 0 ? 1 : 0.3,
                }}
              >
                ...
              </div>
            )}
          </div>

          {/* Decode description */}
          <div
            style={{
              fontSize: 16 * scale,
              color: COLORS.textDim,
              lineHeight: 1.6,
              opacity: showDecodeLabel ? 1 : 0,
            }}
          >
            Tokens generated{" "}
            <span style={{ color: COLORS.decode, fontWeight: 600 }}>
              one at a time
            </span>
            . Each token requires loading all model weights from memory.
          </div>
        </div>
      </div>

      {/* GPU Utilization Bar */}
      <div
        style={{
          position: "absolute",
          bottom: 60 * scale,
          left: 60 * scale,
          right: 60 * scale,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 12 * scale,
          }}
        >
          <span style={{ fontSize: 18 * scale, color: COLORS.text, fontWeight: 600 }}>
            GPU Compute Utilization
          </span>
          <span
            style={{
              fontSize: 24 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color:
                currentGPU > 80
                  ? COLORS.prefill
                  : currentGPU < 30
                  ? COLORS.decode
                  : COLORS.text,
            }}
          >
            {Math.round(currentGPU)}%
          </span>
        </div>
        <div
          style={{
            height: 32 * scale,
            backgroundColor: "#333",
            borderRadius: 16 * scale,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${currentGPU}%`,
              height: "100%",
              backgroundColor:
                currentGPU > 80 ? COLORS.prefill : COLORS.decode,
              borderRadius: 16 * scale,
              transition: "width 0.3s, background-color 0.3s",
              boxShadow: `0 0 ${20 * scale}px ${currentGPU > 80 ? COLORS.prefill : COLORS.decode}60`,
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 8 * scale,
            fontSize: 18 * scale,
            color: COLORS.textDim,
          }}
        >
          <span>Compute-bound (prefill)</span>
          <span>Memory-bound (decode)</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default PhasesScene;
