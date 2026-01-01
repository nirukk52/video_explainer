/**
 * Scene 13: Quantization
 *
 * Key insight: Smaller weights = faster loading from memory.
 * INT4 is 4x smaller than FP16, so up to 4x faster inference.
 *
 * Visual flow:
 * 1. Show FP16 weights (2 bytes per param)
 * 2. Show INT8 compression (1 byte)
 * 3. Show INT4 compression (0.5 bytes)
 * 4. Memory bandwidth savings
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

interface QuantizationSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  fp16: "#ff6b35",
  int8: "#f1c40f",
  int4: "#00ff88",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
};

export const QuantizationScene: React.FC<QuantizationSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Phase timings
  const phase1End = Math.round(durationInFrames * 0.16); // Show FP16
  const phase2End = Math.round(durationInFrames * 0.40); // Show INT8
  const phase3End = Math.round(durationInFrames * 0.64); // Show INT4
  const phase4End = Math.round(durationInFrames * 1.00); // Final stats

  // Format data
  const formats = [
    {
      name: "FP16",
      bytes: 2,
      color: COLORS.fp16,
      size: "14 GB",
      showAt: 0,
      accuracy: "100%",
    },
    {
      name: "INT8",
      bytes: 1,
      color: COLORS.int8,
      size: "7 GB",
      showAt: phase1End,
      accuracy: "99.5%",
    },
    {
      name: "INT4",
      bytes: 0.5,
      color: COLORS.int4,
      size: "3.5 GB",
      showAt: phase2End,
      accuracy: "98%",
    },
  ];

  // Animations
  const introOpacity = interpolate(localFrame, [0, Math.round(durationInFrames * 0.02)], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Current format index
  const currentFormatIndex =
    localFrame < phase1End ? 0 : localFrame < phase2End ? 1 : 2;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.background,
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Scene indicator */}
      <div style={{ ...getSceneIndicatorStyle(scale), opacity: introOpacity }}>
        <span style={getSceneIndicatorTextStyle(scale)}>12</span>
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
          Quantization
        </h1>
        <p style={{ fontSize: 18 * scale, color: COLORS.primary, marginTop: 8 * scale }}>
          Smaller Weights = Faster Loading
        </p>
      </div>

      {/* Main visualization */}
      <div
        style={{
          position: "absolute",
          top: 140 * scale,
          left: 80 * scale,
          right: 80 * scale,
          opacity: introOpacity,
        }}
      >
        {/* Weight representation comparison */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 40 * scale,
            marginBottom: 40 * scale,
          }}
        >
          {formats.map((format, index) => {
            const isVisible = localFrame >= format.showAt;
            const formatOpacity = interpolate(
              localFrame,
              [format.showAt, format.showAt + Math.round(durationInFrames * 0.02)],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            const isActive = index === currentFormatIndex;

            return (
              <div
                key={format.name}
                style={{
                  opacity: formatOpacity,
                  transform: `scale(${isActive ? 1.05 : 1})`,
                  transition: "transform 0.3s",
                }}
              >
                <div
                  style={{
                    padding: 24 * scale,
                    backgroundColor: COLORS.surface,
                    borderRadius: 16 * scale,
                    border: `${3 * scale}px solid ${isActive ? format.color : "#333"}`,
                    width: 200 * scale,
                    textAlign: "center",
                  }}
                >
                  {/* Format name */}
                  <div
                    style={{
                      fontSize: 24 * scale,
                      fontWeight: 700,
                      color: format.color,
                      marginBottom: 16 * scale,
                    }}
                  >
                    {format.name}
                  </div>

                  {/* Bytes visualization */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      gap: 4 * scale,
                      marginBottom: 16 * scale,
                      height: 60 * scale,
                      alignItems: "flex-end",
                    }}
                  >
                    {Array.from({ length: Math.ceil(format.bytes * 2) }).map(
                      (_, i) => (
                        <div
                          key={i}
                          style={{
                            width: 24 * scale,
                            height: 30 * (format.bytes / 2) * 2 * scale,
                            backgroundColor: format.color + "80",
                            borderRadius: 4 * scale,
                            border: `1px solid ${format.color}`,
                          }}
                        />
                      )
                    )}
                  </div>

                  {/* Bytes per param */}
                  <div
                    style={{
                      fontSize: 16 * scale,
                      color: COLORS.textDim,
                      marginBottom: 8 * scale,
                    }}
                  >
                    {format.bytes} bytes/param
                  </div>

                  {/* Model size */}
                  <div
                    style={{
                      fontSize: 32 * scale,
                      fontWeight: 700,
                      fontFamily: "JetBrains Mono",
                      color: format.color,
                      marginBottom: 8 * scale,
                    }}
                  >
                    {format.size}
                  </div>

                  {/* Accuracy */}
                  <div
                    style={{
                      fontSize: 18 * scale,
                      color: COLORS.textDim,
                      padding: `${4 * scale}px ${12 * scale}px`,
                      backgroundColor: "#222",
                      borderRadius: 4 * scale,
                      display: "inline-block",
                    }}
                  >
                    ~{format.accuracy} accuracy
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Memory bandwidth explanation */}
        <div
          style={{
            padding: 24 * scale,
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            border: "1px solid #333",
            textAlign: "center",
            marginBottom: 32 * scale,
            opacity: interpolate(
              localFrame,
              [phase2End, phase2End + Math.round(durationInFrames * 0.04)],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div style={{ fontSize: 18 * scale, color: COLORS.text, marginBottom: 16 * scale }}>
            Memory Bandwidth is the Bottleneck
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: 20 * scale,
            }}
          >
            <div
              style={{
                padding: `${12 * scale}px ${24 * scale}px`,
                backgroundColor: COLORS.fp16 + "20",
                borderRadius: 8 * scale,
                border: `1px solid ${COLORS.fp16}`,
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.fp16 }}>FP16</div>
              <div
                style={{
                  fontSize: 20 * scale,
                  fontWeight: 700,
                  color: COLORS.fp16,
                  fontFamily: "JetBrains Mono",
                }}
              >
                14 GB to load
              </div>
            </div>

            <div style={{ fontSize: 24 * scale, color: COLORS.textDim }}>→</div>

            <div
              style={{
                padding: `${12 * scale}px ${24 * scale}px`,
                backgroundColor: COLORS.int4 + "20",
                borderRadius: 8 * scale,
                border: `1px solid ${COLORS.int4}`,
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.int4 }}>INT4</div>
              <div
                style={{
                  fontSize: 20 * scale,
                  fontWeight: 700,
                  color: COLORS.int4,
                  fontFamily: "JetBrains Mono",
                }}
              >
                3.5 GB to load
              </div>
            </div>

            <div style={{ fontSize: 24 * scale, color: COLORS.textDim }}>=</div>

            <div
              style={{
                padding: `${12 * scale}px ${24 * scale}px`,
                backgroundColor: COLORS.primary + "20",
                borderRadius: 8 * scale,
                border: `1px solid ${COLORS.primary}`,
              }}
            >
              <div style={{ fontSize: 18 * scale, color: COLORS.primary }}>Result</div>
              <div
                style={{
                  fontSize: 20 * scale,
                  fontWeight: 700,
                  color: COLORS.primary,
                  fontFamily: "JetBrains Mono",
                }}
              >
                4× faster
              </div>
            </div>
          </div>
        </div>

        {/* Throughput comparison bars */}
        <div
          style={{
            padding: 24 * scale,
            backgroundColor: COLORS.surface,
            borderRadius: 16 * scale,
            border: "1px solid #333",
            opacity: interpolate(
              localFrame,
              [phase3End, phase3End + Math.round(durationInFrames * 0.04)],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            ),
          }}
        >
          <div
            style={{
              fontSize: 16 * scale,
              color: COLORS.textDim,
              marginBottom: 16 * scale,
              textAlign: "center",
            }}
          >
            Throughput Comparison (tokens/sec)
          </div>

          {formats.map((format, index) => {
            const barWidth = ((2 / format.bytes) * 25); // Inverse of bytes = faster
            const barSpring = spring({
              frame: localFrame - phase3End - index * Math.round(durationInFrames * 0.015),
              fps,
              config: { damping: 15, stiffness: 100 },
            });

            return (
              <div
                key={format.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16 * scale,
                  marginBottom: 12 * scale,
                }}
              >
                <div
                  style={{
                    width: 60 * scale,
                    fontSize: 18 * scale,
                    color: format.color,
                    fontWeight: 600,
                    textAlign: "right",
                  }}
                >
                  {format.name}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: 32 * scale,
                    backgroundColor: "#222",
                    borderRadius: 6 * scale,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${barWidth * barSpring}%`,
                      height: "100%",
                      backgroundColor: format.color,
                      borderRadius: 6 * scale,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      paddingRight: 12 * scale,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 18 * scale,
                        fontWeight: 700,
                        color: "#000",
                      }}
                    >
                      {Math.round(600 * (2 / format.bytes))} tok/s
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
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
            [phase3End + Math.round(durationInFrames * 0.04), phase4End],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
        }}
      >
        <span style={{ fontSize: 22 * scale, color: COLORS.text }}>
          Decode is memory-bound:{" "}
          <span style={{ color: COLORS.int4, fontWeight: 700 }}>
            smaller weights = proportionally faster
          </span>
        </span>
      </div>
    </AbsoluteFill>
  );
};

export default QuantizationScene;
