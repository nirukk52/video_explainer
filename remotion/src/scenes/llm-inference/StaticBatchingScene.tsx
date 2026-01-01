/**
 * Scene 6: The Static Batching Problem
 *
 * Key insight: In static batching, multiple sequences are processed together
 * in the GPU, but shorter sequences finish early and their slots are wasted
 * (idle/padding) while waiting for longer sequences to complete.
 *
 * Visual flow:
 * 1. Show a GPU box with 3 different prompts/sequences
 * 2. Each sequence has a different length
 * 3. Timeline shows sequences progressing
 * 4. Shorter sequences finish first - their slots become "IDLE/WASTE"
 * 5. Show wasted GPU compute while waiting for longest sequence
 */

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS as STYLE_COLORS, getSceneIndicatorStyle, getSceneIndicatorTextStyle } from "./styles";

interface StaticBatchingSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  secondary: "#ff6b35",
  success: "#00ff88",
  waste: "#ff4757",
  idle: "#4a4a5a",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
  gpu: "#2d2d44",
  gpuBorder: "#00d9ff",
  seq1: "#00d9ff", // Short sequence - cyan
  seq2: "#ff6b35", // Medium sequence - orange
  seq3: "#9b59b6", // Long sequence - purple
};

// Three sequences with different lengths
const SEQUENCES = [
  {
    id: 1,
    prompt: "What is 2+2?",
    tokens: 4, // Very short
    color: COLORS.seq1,
    outputTokens: ["4", ".", "EOS", ""],
  },
  {
    id: 2,
    prompt: "Hello there!",
    tokens: 8, // Medium
    color: COLORS.seq2,
    outputTokens: ["Hi", "!", " How", " can", " I", " help", "?", "EOS"],
  },
  {
    id: 3,
    prompt: "Write a haiku...",
    tokens: 16, // Long
    color: COLORS.seq3,
    outputTokens: [
      "Autumn",
      " moon",
      " rises",
      ",",
      " Leaves",
      " fall",
      " gently",
      " down",
      " below",
      ",",
      " Peace",
      " fills",
      " the",
      " night",
      ".",
      "EOS",
    ],
  },
];

const MAX_TOKENS = Math.max(...SEQUENCES.map((s) => s.tokens));

export const StaticBatchingScene: React.FC<StaticBatchingSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const localFrame = frame - startFrame;
  const scale = Math.min(width / 1920, height / 1080);

  // Scaled slot dimensions - larger for mobile readability
  const SLOT_WIDTH = 70 * scale;
  const SLOT_HEIGHT = 56 * scale;
  const SLOT_GAP = 6 * scale;

  // Phase timings
  const phase1End = Math.round(durationInFrames * 0.13); // Intro - show GPU and sequences
  const phase2End = Math.round(durationInFrames * 0.65); // Animation - tokens generating, sequences finishing
  const phase3End = Math.round(durationInFrames * 0.87); // Show waste accumulation
  const phase4End = Math.round(durationInFrames * 1.00); // Final stats

  // Animation progress for token generation (0 to 1)
  const generationProgress = interpolate(
    localFrame,
    [phase1End, phase2End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Current "time step" in the generation (0 to MAX_TOKENS)
  const currentStep = Math.floor(generationProgress * MAX_TOKENS);

  // Calculate waste statistics
  const calculateWaste = () => {
    let totalSlots = 0;
    let wastedSlots = 0;

    for (let step = 0; step < currentStep; step++) {
      for (const seq of SEQUENCES) {
        totalSlots++;
        if (step >= seq.tokens) {
          wastedSlots++;
        }
      }
    }

    return {
      totalSlots,
      wastedSlots,
      wastePercentage:
        totalSlots > 0 ? Math.round((wastedSlots / totalSlots) * 100) : 0,
    };
  };

  const { totalSlots, wastedSlots, wastePercentage } = calculateWaste();

  // Opacities
  const introOpacity = interpolate(localFrame, [0, Math.round(durationInFrames * 0.02)], [0, 1], {
    extrapolateRight: "clamp",
  });

  const wasteHighlightOpacity = interpolate(
    localFrame,
    [phase2End, phase2End + Math.round(durationInFrames * 0.04)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const statsOpacity = interpolate(
    localFrame,
    [phase3End, phase3End + Math.round(durationInFrames * 0.02)],
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
        <span style={getSceneIndicatorTextStyle(scale)}>6</span>
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
          The Static Batching Problem
        </h1>
      </div>

      {/* Main GPU Box Visualization */}
      <div
        style={{
          position: "absolute",
          top: 120 * scale,
          left: "50%",
          transform: "translateX(-50%)",
          opacity: introOpacity,
        }}
      >
        {/* GPU Container */}
        <div
          style={{
            backgroundColor: COLORS.gpu,
            borderRadius: 16 * scale,
            border: `${3 * scale}px solid ${COLORS.gpuBorder}`,
            padding: 24 * scale,
            boxShadow: `0 0 ${30 * scale}px ${COLORS.gpuBorder}30`,
          }}
        >
          {/* GPU Label */}
          <div
            style={{
              textAlign: "center",
              marginBottom: 20 * scale,
            }}
          >
            <span
              style={{
                fontSize: 24 * scale,
                fontWeight: 700,
                color: COLORS.gpuBorder,
                fontFamily: "JetBrains Mono",
              }}
            >
              GPU - Static Batch
            </span>
          </div>

          {/* Sequences in GPU */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 16 * scale,
            }}
          >
            {SEQUENCES.map((seq, seqIndex) => {
              const isComplete = currentStep >= seq.tokens;

              return (
                <div
                  key={seq.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 16 * scale,
                  }}
                >
                  {/* Sequence label */}
                  <div
                    style={{
                      width: 160 * scale,
                      textAlign: "right",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 18 * scale,
                        color: seq.color,
                        fontWeight: 600,
                        marginBottom: 4 * scale,
                      }}
                    >
                      Seq {seq.id}
                    </div>
                    <div
                      style={{
                        fontSize: 16 * scale,
                        color: COLORS.textDim,
                        fontStyle: "italic",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      "{seq.prompt}"
                    </div>
                  </div>

                  {/* Token slots */}
                  <div
                    style={{
                      display: "flex",
                      gap: SLOT_GAP,
                    }}
                  >
                    {Array.from({ length: MAX_TOKENS }).map((_, tokenIndex) => {
                      const isGenerating = tokenIndex < currentStep;
                      const isActiveToken = tokenIndex < seq.tokens;
                      const isWastedSlot =
                        isGenerating && !isActiveToken && tokenIndex < currentStep;
                      const isCurrentlyGenerating =
                        tokenIndex === currentStep - 1 && isActiveToken;

                      // Determine slot appearance
                      let backgroundColor = COLORS.surface;
                      let borderColor = "#333";
                      let content: React.ReactNode = "";

                      if (isGenerating) {
                        if (isActiveToken) {
                          // Active token being generated
                          backgroundColor = seq.color + "60";
                          borderColor = seq.color;
                          content = (
                            <span
                              style={{
                                fontSize: 16 * scale,
                                color: seq.color,
                                fontWeight: 600,
                              }}
                            >
                              {seq.outputTokens[tokenIndex]?.slice(0, 4) ||
                                `T${tokenIndex + 1}`}
                            </span>
                          );
                        } else if (isWastedSlot) {
                          // Wasted/idle slot
                          backgroundColor = COLORS.idle;
                          borderColor = COLORS.waste + "60";
                          content = (
                            <span
                              style={{
                                fontSize: 14 * scale,
                                color: COLORS.waste,
                                fontWeight: 700,
                              }}
                            >
                              IDLE
                            </span>
                          );
                        }
                      }

                      return (
                        <div
                          key={tokenIndex}
                          style={{
                            width: SLOT_WIDTH,
                            height: SLOT_HEIGHT,
                            backgroundColor,
                            border: `${2 * scale}px solid ${borderColor}`,
                            borderRadius: 6 * scale,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            boxShadow: isCurrentlyGenerating
                              ? `0 0 ${10 * scale}px ${seq.color}80`
                              : isWastedSlot
                              ? `0 0 ${8 * scale}px ${COLORS.waste}40`
                              : "none",
                            transition: "all 0.1s ease",
                          }}
                        >
                          {content}
                        </div>
                      );
                    })}
                  </div>

                  {/* Sequence status */}
                  <div
                    style={{
                      width: 90 * scale,
                      textAlign: "center",
                    }}
                  >
                    {isComplete ? (
                      <div
                        style={{
                          padding: `${6 * scale}px ${12 * scale}px`,
                          backgroundColor: COLORS.success + "20",
                          borderRadius: 6 * scale,
                          fontSize: 16 * scale,
                          color: COLORS.success,
                          fontWeight: 600,
                        }}
                      >
                        DONE
                      </div>
                    ) : currentStep > 0 ? (
                      <div
                        style={{
                          padding: `${6 * scale}px ${12 * scale}px`,
                          backgroundColor: seq.color + "20",
                          borderRadius: 6 * scale,
                          fontSize: 16 * scale,
                          color: seq.color,
                          fontWeight: 600,
                        }}
                      >
                        {Math.min(currentStep, seq.tokens)}/{seq.tokens}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Timeline / Progress indicator */}
          <div
            style={{
              marginTop: 24 * scale,
              padding: `${16 * scale}px 0`,
              borderTop: `${1 * scale}px solid ${COLORS.textDim}40`,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12 * scale,
                marginBottom: 8 * scale,
              }}
            >
              <span
                style={{
                  fontSize: 18 * scale,
                  color: COLORS.textDim,
                  width: 140 * scale,
                  textAlign: "right",
                }}
              >
                Time Step:
              </span>
              <div
                style={{
                  flex: 1,
                  height: 8 * scale,
                  backgroundColor: COLORS.surface,
                  borderRadius: 4 * scale,
                  overflow: "hidden",
                  position: "relative",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${(currentStep / MAX_TOKENS) * 100}%`,
                    backgroundColor: COLORS.primary,
                    borderRadius: 4 * scale,
                    transition: "width 0.1s ease",
                  }}
                />
                {/* Markers for when each sequence finishes */}
                {SEQUENCES.map((seq) => (
                  <div
                    key={seq.id}
                    style={{
                      position: "absolute",
                      left: `${(seq.tokens / MAX_TOKENS) * 100}%`,
                      top: -4 * scale,
                      bottom: -4 * scale,
                      width: 2 * scale,
                      backgroundColor: seq.color,
                    }}
                  />
                ))}
              </div>
              <span
                style={{
                  fontSize: 16 * scale,
                  color: COLORS.primary,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  width: 60 * scale,
                }}
              >
                {currentStep}/{MAX_TOKENS}
              </span>
            </div>

            {/* Legend */}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: 32 * scale,
                marginTop: 16 * scale,
              }}
            >
              {SEQUENCES.map((seq) => (
                <div
                  key={seq.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10 * scale,
                  }}
                >
                  <div
                    style={{
                      width: 20 * scale,
                      height: 20 * scale,
                      backgroundColor: seq.color,
                      borderRadius: 4 * scale,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 18 * scale,
                      color: COLORS.textDim,
                    }}
                  >
                    Seq {seq.id}: {seq.tokens} tokens
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Waste Statistics */}
      <div
        style={{
          position: "absolute",
          bottom: 140 * scale,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 60 * scale,
          opacity: statsOpacity,
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 56 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color: COLORS.waste,
            }}
          >
            {wastedSlots}
          </div>
          <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
            Wasted GPU Slots
          </div>
        </div>

        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 56 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color: COLORS.primary,
            }}
          >
            {totalSlots - wastedSlots}
          </div>
          <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
            Useful Work
          </div>
        </div>

        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 56 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color: COLORS.waste,
            }}
          >
            {wastePercentage}%
          </div>
          <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
            GPU Waste
          </div>
        </div>
      </div>

      {/* Waste highlight box */}
      <div
        style={{
          position: "absolute",
          bottom: 60 * scale,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: wasteHighlightOpacity,
        }}
      >
        <div
          style={{
            display: "inline-block",
            backgroundColor: COLORS.waste + "20",
            border: `${2 * scale}px solid ${COLORS.waste}`,
            borderRadius: 12 * scale,
            padding: `${12 * scale}px ${32 * scale}px`,
          }}
        >
          <span
            style={{
              fontSize: 24 * scale,
              color: COLORS.waste,
            }}
          >
            <span style={{ fontWeight: 700 }}>Short sequences wait</span> for
            long ones.{" "}
            <span
              style={{
                color: COLORS.idle,
                fontFamily: "JetBrains Mono",
              }}
            >
              IDLE
            </span>{" "}
            slots waste compute.
          </span>
        </div>
      </div>

      {/* Explanation text during generation */}
      {localFrame > phase1End && localFrame < phase2End && (
        <div
          style={{
            position: "absolute",
            bottom: 40 * scale,
            left: 0,
            right: 0,
            textAlign: "center",
            opacity: interpolate(
              localFrame,
              [phase1End, phase1End + Math.round(durationInFrames * 0.02)],
              [0, 1],
              { extrapolateRight: "clamp" }
            ),
          }}
        >
          <span style={{ fontSize: 26 * scale, color: COLORS.text }}>
            {currentStep < SEQUENCES[0].tokens ? (
              <>All sequences generating in parallel...</>
            ) : currentStep < SEQUENCES[1].tokens ? (
              <>
                <span style={{ color: COLORS.seq1 }}>Seq 1</span> finished! But
                its slot sits{" "}
                <span style={{ color: COLORS.waste }}>idle</span>...
              </>
            ) : currentStep < SEQUENCES[2].tokens ? (
              <>
                <span style={{ color: COLORS.seq1 }}>Seq 1</span> and{" "}
                <span style={{ color: COLORS.seq2 }}>Seq 2</span> done. Waiting
                for <span style={{ color: COLORS.seq3 }}>Seq 3</span>...
              </>
            ) : (
              <>
                Finally done! But{" "}
                <span style={{ color: COLORS.waste }}>
                  {wastePercentage}% of GPU was wasted
                </span>
              </>
            )}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};

export default StaticBatchingScene;
