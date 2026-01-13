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
  Easing,
} from "remotion";
import {
  TransitionSeries,
  springTiming,
} from "@remotion/transitions";
import { getSceneByPath } from "./index";
import { cinematicFade, cinematicSlide } from "../components/CinematicTransition";
import {
  PersistentParticles,
  Vignette,
  AmbientGlow,
} from "../components/CinematicEffects";

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
 * Background music configuration
 */
export interface BackgroundMusicConfig {
  /** Path to the music file (relative to public directory) */
  path: string;
  /** Volume level (0-1), defaults to 0.1 */
  volume?: number;
}

/**
 * Audio configuration
 */
export interface AudioConfig {
  voiceover_dir: string;
  buffer_between_scenes_seconds: number;
  /** Optional background music configuration */
  background_music?: BackgroundMusicConfig;
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

// Transition duration in frames (at 30fps) - SLOWER for cinematic feel
const TRANSITION_DURATION_FRAMES = 45; // ~1.5 seconds for smooth, cinematic transitions

// Cinematic transition styles - fewer, more elegant options
type TransitionStyle = "cinematicFade" | "cinematicSlideLeft" | "cinematicSlideRight" | "cinematicSlideUp" | "simpleFade";

const TRANSITION_STYLES: TransitionStyle[] = [
  "cinematicFade",      // Focus blur + light leak + chromatic
  "cinematicSlideLeft", // Slide with blur + effects
  "cinematicFade",      // More fades for elegance
  "cinematicSlideRight",
  "cinematicFade",
  "cinematicSlideUp",
  "simpleFade",         // Occasional simple fade for variety
  "cinematicFade",
];

// Deterministic selection based on scene index (consistent across renders)
const getTransitionStyle = (sceneIndex: number): TransitionStyle => {
  const hash = (sceneIndex * 7 + 3) % TRANSITION_STYLES.length;
  return TRANSITION_STYLES[hash];
};

// Get the cinematic transition presentation based on style
const getTransitionPresentation = (style: TransitionStyle, accentColor: string = "#00d9ff") => {
  switch (style) {
    case "cinematicFade":
      return cinematicFade({
        accentColor,
        enableBlur: true,
        enableLightLeak: true,
        enableChromatic: true,
        enableColorPulse: true,
      });
    case "cinematicSlideLeft":
      return cinematicSlide({
        slideDirection: "left",
        accentColor,
        enableBlur: true,
        enableLightLeak: true,
        enableColorPulse: true,
      });
    case "cinematicSlideRight":
      return cinematicSlide({
        slideDirection: "right",
        accentColor,
        enableBlur: true,
        enableLightLeak: true,
        enableColorPulse: true,
      });
    case "cinematicSlideUp":
      return cinematicSlide({
        slideDirection: "up",
        accentColor,
        enableBlur: true,
        enableLightLeak: true,
        enableColorPulse: true,
      });
    case "simpleFade":
      // Use cinematic fade with minimal effects for subtle variety
      return cinematicFade({
        accentColor,
        enableBlur: false,
        enableLightLeak: false,
        enableChromatic: false,
        enableColorPulse: false,
      });
    default:
      return cinematicFade({ accentColor });
  }
};

/**
 * Scene content wrapper - renders ONLY the visual scene (no audio)
 * Audio is handled separately to avoid double-playback during transitions
 */
const SceneContent: React.FC<{
  scene: StoryboardScene & { SceneComponent: React.FC<{ startFrame: number }> | null };
}> = ({ scene }) => {
  return (
    <AbsoluteFill>
      {scene.SceneComponent ? (
        <scene.SceneComponent startFrame={0} />
      ) : (
        <MissingScene sceneType={scene.type} />
      )}
    </AbsoluteFill>
  );
};

/**
 * Background music component with fade-in and fade-out effects
 * Plays throughout the entire video with looping support
 *
 * Wrapped in a Sequence to ensure proper timing across the full composition.
 */
const BackgroundMusic: React.FC<{
  musicPath: string;
  volume: number;
  totalDurationInFrames: number;
}> = ({ musicPath, volume, totalDurationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade-in: first 2 seconds
  const fadeInDurationFrames = 2 * fps;
  // Fade-out: last 3 seconds
  const fadeOutDurationFrames = 3 * fps;

  // Calculate fade-in volume (0 -> target volume over first 2 seconds)
  const fadeInVolume = interpolate(
    frame,
    [0, fadeInDurationFrames],
    [0, volume],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    }
  );

  // Calculate fade-out volume (target volume -> 0 over last 3 seconds)
  const fadeOutVolume = interpolate(
    frame,
    [totalDurationInFrames - fadeOutDurationFrames, totalDurationInFrames],
    [volume, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.in(Easing.cubic),
    }
  );

  // Combined volume: use fade-in at start, fade-out at end, full volume in between
  const currentVolume = Math.min(fadeInVolume, fadeOutVolume);

  return (
    <Sequence from={0} durationInFrames={totalDurationInFrames} name="Background Music">
      <Audio
        src={staticFile(musicPath)}
        volume={currentVolume}
        loop
      />
    </Sequence>
  );
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

  // Prepare scene data with components
  const sceneData = storyboard.scenes.map((scene, index) => {
    // Scene duration = audio duration + buffer
    const baseDurationSeconds = scene.audio_duration_seconds + buffer;
    const baseDurationInFrames = Math.ceil(baseDurationSeconds * fps);

    // Add transition padding so narration completes BEFORE the transition begins
    // The transition overlaps the last N frames, so we extend the scene
    // so the content (and audio) finishes before the crossfade starts
    const isLastScene = index === storyboard.scenes.length - 1;
    const transitionPadding = isLastScene ? 0 : TRANSITION_DURATION_FRAMES;
    const durationInFrames = baseDurationInFrames + transitionPadding;

    // Look up scene component from registry
    const SceneComponent = getSceneByPath(scene.type);

    return {
      ...scene,
      durationInFrames,
      durationSeconds: durationInFrames / fps,
      SceneComponent,
    };
  });

  // Calculate total duration for background music
  const totalDurationInFrames = sceneData.reduce(
    (sum, scene) => sum + scene.durationInFrames,
    0
  ) - (sceneData.length - 1) * TRANSITION_DURATION_FRAMES; // Account for overlapping transitions

  // Background music configuration
  const backgroundMusic = storyboard.audio?.background_music;
  const musicVolume = backgroundMusic?.volume ?? 0.1;

  // Get accent color from style config
  const accentColor = storyboard.style?.primary_color || "#00d9ff";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: storyboard.style?.background_color || "#0f0f1a",
      }}
    >
      {/* Background music - plays throughout entire video with fade-in/fade-out */}
      {backgroundMusic?.path && (
        <BackgroundMusic
          musicPath={backgroundMusic.path}
          volume={musicVolume}
          totalDurationInFrames={totalDurationInFrames}
        />
      )}

      {/* Ambient glow from bottom - subtle colored lighting */}
      <AmbientGlow color={accentColor} intensity={0.12} />

      {/* TransitionSeries for smooth overlapping VISUAL transitions only */}
      <TransitionSeries>
        {sceneData.map((scene, index) => {
          const transitionStyle = getTransitionStyle(index);
          const isLastScene = index === sceneData.length - 1;

          return (
            <React.Fragment key={scene.id}>
              <TransitionSeries.Sequence durationInFrames={scene.durationInFrames}>
                <SceneContent scene={scene} />
              </TransitionSeries.Sequence>

              {/* Add transition between scenes (not after last scene) */}
              {!isLastScene && (
                <TransitionSeries.Transition
                  presentation={getTransitionPresentation(transitionStyle, accentColor)}
                  timing={springTiming({
                    config: { damping: 200 },
                    durationInFrames: TRANSITION_DURATION_FRAMES,
                    durationRestThreshold: 0.001,
                  })}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>

      {/* Audio layer - sequential voiceovers that DON'T overlap during transitions */}
      {(() => {
        let audioStartFrame = 0;
        return sceneData.map((scene, index) => {
          const currentStart = audioStartFrame;
          // Audio duration in frames (just the audio, not the visual padding)
          const audioDurationFrames = Math.ceil(scene.audio_duration_seconds * fps);
          // Full scene duration for calculating next start
          const sceneVisualDuration = scene.durationInFrames;
          // Next scene starts after this scene minus the transition overlap
          const isLastScene = index === sceneData.length - 1;
          audioStartFrame += sceneVisualDuration - (isLastScene ? 0 : TRANSITION_DURATION_FRAMES);

          const audioPath = `${voiceoverBasePath}/${scene.audio_file}`;

          return (
            <React.Fragment key={`audio-${scene.id}`}>
              {/* Voiceover */}
              <Sequence
                from={currentStart}
                durationInFrames={audioDurationFrames + Math.ceil(buffer * fps)}
                name={`Audio: ${scene.title}`}
              >
                <Audio src={staticFile(audioPath)} volume={1} />
              </Sequence>

              {/* SFX cues for this scene */}
              {scene.sfx_cues?.map((cue, cueIndex) => (
                <Sequence
                  key={`sfx-${scene.id}-${cueIndex}`}
                  from={currentStart + cue.frame}
                  durationInFrames={cue.duration_frames || 60}
                  name={`SFX: ${cue.sound}`}
                >
                  <Audio
                    src={staticFile(`sfx/${cue.sound}.wav`)}
                    volume={cue.volume ?? 0.1}
                  />
                </Sequence>
              ))}
            </React.Fragment>
          );
        });
      })()}

      {/* Persistent floating particles - dust motes for cinematic depth */}
      <PersistentParticles count={25} color="#ffffff" seed="cinematic-dust" />

      {/* Vignette overlay - darkened edges for focus */}
      <Vignette intensity={0.35} />
    </AbsoluteFill>
  );
};

/**
 * Calculate total duration from storyboard (accounting for overlapping transitions)
 *
 * With TransitionSeries:
 * - Each scene (except last) has transitionPadding added so audio finishes before transition
 * - Transitions overlap by TRANSITION_DURATION_FRAMES
 * - The padding and overlap cancel out, so total = sum(audio + buffer)
 */
export function calculateStoryboardDuration(storyboard: SceneStoryboard, fps: number = 30): number {
  const buffer = storyboard.audio?.buffer_between_scenes_seconds ?? 1.0;

  // Total duration is simply the sum of all audio durations plus buffers
  // The transition padding and overlap cancel each other out
  const totalDuration = storyboard.scenes.reduce(
    (sum, scene) => sum + scene.audio_duration_seconds + buffer,
    0
  );

  return totalDuration;
}

/**
 * Dynamic Storyboard Player - loads storyboard from build-time injection or props
 *
 * For dev preview: Uses storyboard injected at build time via webpack DefinePlugin
 * For rendering: Pass the storyboard prop directly to SceneStoryboardPlayer
 *
 * The storyboard is loaded from process.env.__STORYBOARD_JSON__ which is set
 * in remotion.config.ts based on the PROJECT environment variable.
 */

// Get build-time injected storyboard (set in remotion.config.ts)
const getInjectedStoryboard = (): SceneStoryboard | null => {
  try {
    // This is replaced at build time by webpack DefinePlugin
    const injected = process.env.__STORYBOARD_JSON__;
    if (injected && typeof injected === "object") {
      return injected as unknown as SceneStoryboard;
    }
    return null;
  } catch {
    return null;
  }
};

export const DynamicStoryboardPlayer: React.FC<SceneStoryboardPlayerProps> = ({
  storyboard: providedStoryboard,
  voiceoverBasePath = "voiceover",
}) => {
  // Priority: props > build-time injection
  const storyboard = providedStoryboard || getInjectedStoryboard();

  if (!storyboard) {
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
        <div style={{ fontSize: 48, fontWeight: 700, color: "#ff4757", marginBottom: 20 }}>
          No Storyboard Found
        </div>
        <div style={{ fontSize: 24, color: "#888" }}>
          Make sure storyboard/storyboard.json exists in your project
        </div>
        <div style={{ fontSize: 18, color: "#666", marginTop: 20 }}>
          Run with: PROJECT=your-project npm run dev
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <SceneStoryboardPlayer
      storyboard={storyboard}
      voiceoverBasePath={voiceoverBasePath}
    />
  );
};

export default SceneStoryboardPlayer;
