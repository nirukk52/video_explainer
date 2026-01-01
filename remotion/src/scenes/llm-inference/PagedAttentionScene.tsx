/**
 * Scene 12: PagedAttention
 *
 * Key insight: Like OS virtual memory, allocate KV cache in blocks.
 * No pre-allocation, no fragmentation, 95%+ memory utilization.
 *
 * Visual flow:
 * 1. Show problem: giant pre-allocated buffers
 * 2. Introduce blocks concept (like memory pages)
 * 3. Show on-demand allocation
 * 4. Blocks returning to free list
 * 5. Memory utilization improvement
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

interface PagedAttentionSceneProps {
  startFrame?: number;
}

const COLORS = {
  background: "#0f0f1a",
  primary: "#00d9ff",
  block: "#9b59b6",
  free: "#2ecc71",
  used: "#ff6b35",
  text: "#ffffff",
  textDim: "#888888",
  surface: "#1a1a2e",
};

const NUM_BLOCKS = 24;
const BLOCK_SIZE = 16; // tokens per block

export const PagedAttentionScene: React.FC<PagedAttentionSceneProps> = ({
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const scale = Math.min(width / 1920, height / 1080);
  const localFrame = frame - startFrame;

  // Phase timings
  const phase1End = Math.round(durationInFrames * 0.14); // Intro - virtual memory concept
  const phase2End = Math.round(durationInFrames * 0.43); // Block allocation animation
  const phase3End = Math.round(durationInFrames * 0.71); // Deallocation
  const phase4End = Math.round(durationInFrames * 1.00); // Stats

  // Animation for blocks being allocated
  const allocationProgress = interpolate(
    localFrame,
    [phase1End, phase2End],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Sequences requesting blocks
  const sequences = [
    { id: "A", blocksNeeded: 3, color: "#00d9ff", startsAt: 0 },
    { id: "B", blocksNeeded: 5, color: "#ff6b35", startsAt: 0.2 },
    { id: "C", blocksNeeded: 2, color: "#00ff88", startsAt: 0.4 },
    { id: "D", blocksNeeded: 4, color: "#f1c40f", startsAt: 0.6 },
  ];

  // Calculate block states
  const getBlockStates = () => {
    const states: Array<{ owner: string | null; color: string }> = Array(NUM_BLOCKS)
      .fill(null)
      .map(() => ({ owner: null, color: COLORS.free }));

    let blockIndex = 0;
    for (const seq of sequences) {
      if (allocationProgress >= seq.startsAt) {
        const blocksToAllocate = Math.floor(
          seq.blocksNeeded * Math.min(1, (allocationProgress - seq.startsAt) / 0.3)
        );
        for (let i = 0; i < blocksToAllocate && blockIndex < NUM_BLOCKS; i++) {
          states[blockIndex] = { owner: seq.id, color: seq.color };
          blockIndex++;
        }
      }
    }

    // After phase3, some blocks get freed
    if (localFrame > phase2End + Math.round(durationInFrames * 0.07)) {
      const freeProgress = interpolate(
        localFrame,
        [phase2End + Math.round(durationInFrames * 0.07), phase3End],
        [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      );

      // Free sequence A's blocks
      if (freeProgress > 0.3) {
        for (let i = 0; i < 3; i++) {
          states[i] = { owner: null, color: COLORS.free };
        }
      }
    }

    return states;
  };

  const blockStates = getBlockStates();
  const usedBlocks = blockStates.filter((b) => b.owner !== null).length;
  const freeBlocks = NUM_BLOCKS - usedBlocks;

  // Animations
  const introOpacity = interpolate(localFrame, [0, Math.round(durationInFrames * 0.02)], [0, 1], {
    extrapolateRight: "clamp",
  });

  const conceptOpacity = interpolate(
    localFrame,
    [Math.round(durationInFrames * 0.04), Math.round(durationInFrames * 0.07)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const statsOpacity = interpolate(
    localFrame,
    [phase3End, phase3End + Math.round(durationInFrames * 0.04)],
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
          PagedAttention
        </h1>
        <p
          style={{
            fontSize: 18 * scale,
            color: COLORS.block,
            marginTop: 8 * scale,
            opacity: conceptOpacity,
          }}
        >
          Virtual Memory for KV Cache
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
        {/* Block pool visualization */}
        <div
          style={{
            marginBottom: 32 * scale,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 16 * scale,
            }}
          >
            <span style={{ color: COLORS.textDim, fontSize: 16 * scale }}>
              GPU Memory Block Pool ({BLOCK_SIZE} tokens per block)
            </span>
            <div style={{ display: "flex", gap: 16 * scale }}>
              <span style={{ color: COLORS.free, fontSize: 14 * scale }}>
                Free: {freeBlocks}
              </span>
              <span style={{ color: COLORS.used, fontSize: 14 * scale }}>
                Used: {usedBlocks}
              </span>
            </div>
          </div>

          {/* Block grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(12, 1fr)",
              gap: 8 * scale,
              padding: 20 * scale,
              backgroundColor: COLORS.surface,
              borderRadius: 12 * scale,
              border: `2px solid ${COLORS.block}40`,
            }}
          >
            {blockStates.map((block, index) => {
              const blockSpring = spring({
                frame: localFrame - (index * 2),
                fps,
                config: { damping: 15, stiffness: 200 },
              });

              return (
                <div
                  key={index}
                  style={{
                    aspectRatio: "1",
                    backgroundColor: block.owner ? block.color + "60" : COLORS.free + "20",
                    borderRadius: 6 * scale,
                    border: `2px solid ${block.owner ? block.color : COLORS.free}40`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18 * scale,
                    fontWeight: 600,
                    color: block.owner ? block.color : COLORS.free,
                    transform: `scale(${0.9 + blockSpring * 0.1})`,
                  }}
                >
                  {block.owner || "Free"}
                </div>
              );
            })}
          </div>
        </div>

        {/* Sequence block tables */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 24 * scale,
            marginBottom: 32 * scale,
            opacity: conceptOpacity,
          }}
        >
          {sequences.map((seq) => {
            const isActive = allocationProgress >= seq.startsAt;
            const allocatedBlocks = isActive
              ? Math.floor(seq.blocksNeeded * Math.min(1, (allocationProgress - seq.startsAt) / 0.3))
              : 0;

            return (
              <div
                key={seq.id}
                style={{
                  padding: 16 * scale,
                  backgroundColor: COLORS.surface,
                  borderRadius: 12 * scale,
                  border: `2px solid ${isActive ? seq.color : "#333"}`,
                  opacity: isActive ? 1 : 0.5,
                  minWidth: 140 * scale,
                }}
              >
                <div
                  style={{
                    fontSize: 18 * scale,
                    fontWeight: 600,
                    color: seq.color,
                    marginBottom: 8 * scale,
                    textAlign: "center",
                  }}
                >
                  Sequence {seq.id}
                </div>
                <div
                  style={{
                    fontSize: 18 * scale,
                    color: COLORS.textDim,
                    textAlign: "center",
                  }}
                >
                  Block Table
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 4 * scale,
                    marginTop: 8 * scale,
                    justifyContent: "center",
                  }}
                >
                  {Array.from({ length: seq.blocksNeeded }).map((_, i) => (
                    <div
                      key={i}
                      style={{
                        width: 24 * scale,
                        height: 24 * scale,
                        backgroundColor:
                          i < allocatedBlocks ? seq.color + "60" : "#333",
                        borderRadius: 4 * scale,
                        border: `1px solid ${seq.color}40`,
                      }}
                    />
                  ))}
                </div>
                <div
                  style={{
                    fontSize: 18 * scale,
                    color: COLORS.textDim,
                    textAlign: "center",
                    marginTop: 8 * scale,
                  }}
                >
                  {allocatedBlocks * BLOCK_SIZE} tokens
                </div>
              </div>
            );
          })}
        </div>

        {/* Key features */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 32 * scale,
          }}
        >
          {[
            { icon: "1", label: "On-demand allocation", desc: "Blocks allocated as needed" },
            { icon: "2", label: "No fragmentation", desc: "Blocks are uniform size" },
            { icon: "3", label: "Free list reuse", desc: "Completed blocks recycled" },
          ].map((feature, i) => (
            <div
              key={i}
              style={{
                textAlign: "center",
                padding: 16 * scale,
                backgroundColor: COLORS.surface,
                borderRadius: 12 * scale,
                border: "1px solid #333",
                opacity: interpolate(
                  localFrame,
                  [phase1End + i * Math.round(durationInFrames * 0.03), phase1End + i * Math.round(durationInFrames * 0.03) + Math.round(durationInFrames * 0.02)],
                  [0, 1],
                  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                ),
              }}
            >
              <div
                style={{
                  width: 32 * scale,
                  height: 32 * scale,
                  borderRadius: "50%",
                  backgroundColor: COLORS.block + "40",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: `0 auto ${8 * scale}px`,
                  fontSize: 16 * scale,
                  fontWeight: 700,
                  color: COLORS.block,
                }}
              >
                {feature.icon}
              </div>
              <div
                style={{ fontSize: 18 * scale, color: COLORS.text, marginBottom: 4 * scale }}
              >
                {feature.label}
              </div>
              <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
                {feature.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div
        style={{
          position: "absolute",
          bottom: 140 * scale,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 80 * scale,
          opacity: statsOpacity,
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 56 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color: "#ff4757",
            }}
          >
            20%
          </div>
          <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
            Before (Pre-allocation)
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 32 * scale,
            color: COLORS.textDim,
          }}
        >
          →
        </div>

        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 56 * scale,
              fontWeight: 700,
              fontFamily: "JetBrains Mono",
              color: COLORS.free,
            }}
          >
            95%+
          </div>
          <div style={{ fontSize: 18 * scale, color: COLORS.textDim }}>
            After (PagedAttention)
          </div>
        </div>
      </div>

      {/* Key insight */}
      <div
        style={{
          position: "absolute",
          bottom: 50 * scale,
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
          <span style={{ color: COLORS.block, fontWeight: 700 }}>3×</span> more
          sequences per batch ={" "}
          <span style={{ color: COLORS.free, fontWeight: 700 }}>3×</span> higher
          throughput
        </span>
      </div>
    </AbsoluteFill>
  );
};

export default PagedAttentionScene;
