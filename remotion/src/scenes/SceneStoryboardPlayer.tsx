/**
 * SceneStoryboardPlayer - Data-driven scene renderer
 *
 * Renders a video from a storyboard.json file that references scene components
 * by type path (e.g., "llm-inference/hook").
 *
 * This approach allows:
 * - Scene components to be reused across projects
 * - Project-specific data (audio, timing) to live in project directories
 * - Easy creation of new videos by just creating new storyboard.json files
 */

import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Audio,
  staticFile,
  useVideoConfig,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { getSceneByPath } from "./index";

/**
 * SFX cue definition - frame-accurate sound effect trigger
 */
export interface SFXCue {
  /** Sound file name (without extension, looked up in sfx/ directory) */
  sound: string;
  /** Frame offset from scene start when sound should play */
  frame: number;
  /** Volume (0-1), defaults to 0.1 for subtle mix */
  volume?: number;
  /** Optional duration in frames (for looping sounds) */
  duration_frames?: number;
}

/**
 * Scene definition in storyboard.json
 */
export interface StoryboardScene {
  id: string;
  type: string; // e.g., "llm-inference/hook"
  title: string;
  audio_file: string;
  audio_duration_seconds: number;
  /** Frame-accurate SFX cues for this scene */
  sfx_cues?: SFXCue[];
}

/**
 * Video configuration
 */
export interface VideoConfig {
  width: number;
  height: number;
  fps: number;
}

/**
 * Style configuration
 */
export interface StyleConfig {
  background_color: string;
  primary_color: string;
  secondary_color: string;
  font_family: string;
}

/**
 * Audio configuration
 */
export interface AudioConfig {
  voiceover_dir: string;
  buffer_between_scenes_seconds: number;
}

/**
 * Scene-based storyboard format
 */
export interface SceneStoryboard {
  title: string;
  description: string;
  version: string;
  project: string;
  video: VideoConfig;
  style: StyleConfig;
  scenes: StoryboardScene[];
  audio: AudioConfig;
  total_duration_seconds: number;
}

export interface SceneStoryboardPlayerProps {
  storyboard?: SceneStoryboard;
  /** Base path for voiceover files (for staticFile) */
  voiceoverBasePath?: string;
}

// Transition duration in seconds
const TRANSITION_DURATION = 0.5;

/**
 * Fade transition component
 */
const FadeTransition: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
}> = ({ children, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const transitionFrames = Math.floor(TRANSITION_DURATION * fps);

  // Fade in at start
  const fadeIn = interpolate(frame, [0, transitionFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - transitionFrames, durationInFrames],
    [1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const opacity = Math.min(fadeIn, fadeOut);

  return <div style={{ opacity }}>{children}</div>;
};

/**
 * Fallback scene for missing components
 */
const MissingScene: React.FC<{ sceneType: string }> = ({ sceneType }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#1a1a2e",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 48,
          fontWeight: 700,
          color: "#ff4757",
          marginBottom: 20,
        }}
      >
        Scene Not Found
      </div>
      <div
        style={{
          fontSize: 24,
          color: "#888",
        }}
      >
        Missing: {sceneType}
      </div>
    </AbsoluteFill>
  );
};

// Empty storyboard for fallback
const emptyStoryboard: SceneStoryboard = {
  title: "Empty",
  description: "",
  version: "2.0.0",
  project: "empty",
  video: { width: 1920, height: 1080, fps: 30 },
  style: {
    background_color: "#0f0f1a",
    primary_color: "#00d9ff",
    secondary_color: "#ff6b35",
    font_family: "Inter",
  },
  scenes: [],
  audio: { voiceover_dir: "voiceover", buffer_between_scenes_seconds: 1.0 },
  total_duration_seconds: 0,
};

export const SceneStoryboardPlayer: React.FC<SceneStoryboardPlayerProps> = ({
  storyboard = emptyStoryboard,
  voiceoverBasePath = "voiceover",
}) => {
  const { fps } = useVideoConfig();
  const buffer = storyboard.audio?.buffer_between_scenes_seconds ?? 1.0;

  // Calculate frame offsets for each scene
  let currentFrame = 0;
  const sceneData = storyboard.scenes.map((scene) => {
    const startFrame = currentFrame;
    // Scene duration = audio duration + buffer
    const durationSeconds = scene.audio_duration_seconds + buffer;
    const durationInFrames = Math.ceil(durationSeconds * fps);
    currentFrame += durationInFrames;

    // Look up scene component from registry
    const SceneComponent = getSceneByPath(scene.type);

    return {
      ...scene,
      startFrame,
      durationInFrames,
      durationSeconds,
      SceneComponent,
    };
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: storyboard.style?.background_color || "#0f0f1a",
      }}
    >
      {sceneData.map((scene, index) => {
        const SceneComponent = scene.SceneComponent;
        const audioPath = `${voiceoverBasePath}/${scene.audio_file}`;

        return (
          <Sequence
            key={scene.id}
            from={scene.startFrame}
            durationInFrames={scene.durationInFrames}
            name={`Scene ${index + 1}: ${scene.title}`}
          >
            {/* Visual content with fade transition */}
            <FadeTransition durationInFrames={scene.durationInFrames}>
              {SceneComponent ? (
                <SceneComponent startFrame={0} />
              ) : (
                <MissingScene sceneType={scene.type} />
              )}
            </FadeTransition>

            {/* Voiceover/mixed audio track */}
            <Audio src={staticFile(audioPath)} volume={1} />

            {/* Frame-accurate SFX cues */}
            {scene.sfx_cues?.map((cue, cueIndex) => (
              <Sequence
                key={`sfx-${scene.id}-${cueIndex}`}
                from={cue.frame}
                durationInFrames={cue.duration_frames || 60}
                name={`SFX: ${cue.sound}`}
              >
                <Audio
                  src={staticFile(`sfx/${cue.sound}.wav`)}
                  volume={cue.volume ?? 0.1}
                />
              </Sequence>
            ))}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * Calculate total duration from storyboard
 */
export function calculateStoryboardDuration(storyboard: SceneStoryboard): number {
  const buffer = storyboard.audio?.buffer_between_scenes_seconds ?? 1.0;
  return storyboard.scenes.reduce(
    (sum, scene) => sum + scene.audio_duration_seconds + buffer,
    0
  );
}

export default SceneStoryboardPlayer;
