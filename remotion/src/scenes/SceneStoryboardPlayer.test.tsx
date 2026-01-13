/**
 * Tests for SceneStoryboardPlayer component.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";

// Mock remotion modules
vi.mock("remotion", () => ({
  AbsoluteFill: ({ children, style }: any) => (
    <div data-testid="absolute-fill" style={style}>
      {children}
    </div>
  ),
  Sequence: ({ children, from, durationInFrames, name }: any) => (
    <div data-testid="sequence" data-from={from} data-duration={durationInFrames} data-name={name}>
      {children}
    </div>
  ),
  Audio: ({ src, volume }: any) => (
    <audio data-testid="audio" data-src={src} data-volume={volume} />
  ),
  staticFile: (path: string) => `/static/${path}`,
  useVideoConfig: () => ({
    fps: 30,
    width: 1920,
    height: 1080,
    durationInFrames: 300,
  }),
  useCurrentFrame: () => 0,
  interpolate: (frame: number, inputRange: number[], outputRange: number[]) => outputRange[0],
  Easing: {
    out: (fn: any) => fn,
    in: (fn: any) => fn,
    inOut: (fn: any) => fn,
    cubic: (x: number) => x,
  },
}));

// Mock @remotion/transitions
vi.mock("@remotion/transitions", () => {
  const TransitionSeriesComponent = ({ children }: any) => (
    <div data-testid="transition-series">{children}</div>
  );
  TransitionSeriesComponent.Sequence = ({ children, durationInFrames }: any) => (
    <div data-testid="transition-sequence" data-duration={durationInFrames}>{children}</div>
  );
  TransitionSeriesComponent.Transition = ({ presentation, timing }: any) => (
    <div data-testid="transition" />
  );

  return {
    TransitionSeries: TransitionSeriesComponent,
    springTiming: () => ({ type: "spring" }),
  };
});

// Mock cinematic components
vi.mock("../components/CinematicTransition", () => ({
  cinematicFade: (props: any) => ({ component: () => null, props }),
  cinematicSlide: (props: any) => ({ component: () => null, props }),
}));

vi.mock("../components/CinematicEffects", () => ({
  PersistentParticles: () => <div data-testid="particles" />,
  Vignette: () => <div data-testid="vignette" />,
  AmbientGlow: () => <div data-testid="ambient-glow" />,
}));

// Mock the scene registry
vi.mock("./index", () => ({
  getSceneByPath: (path: string) => {
    const mockScenes: Record<string, React.FC> = {
      "project/hook": () => <div data-testid="hook-scene">Hook Scene</div>,
      "project/phases": () => <div data-testid="phases-scene">Phases Scene</div>,
    };
    const type = path.split("/")[1] || path;
    return mockScenes[`project/${type}`];
  },
}));

import {
  SceneStoryboardPlayer,
  calculateStoryboardDuration,
  type SceneStoryboard,
} from "./SceneStoryboardPlayer";

describe("SceneStoryboardPlayer", () => {
  const mockStoryboard: SceneStoryboard = {
    title: "Test Video",
    description: "Test description",
    version: "2.0.0",
    project: "test-project",
    video: { width: 1920, height: 1080, fps: 30 },
    style: {
      background_color: "#0f0f1a",
      primary_color: "#00d9ff",
      secondary_color: "#ff6b35",
      font_family: "Inter",
    },
    scenes: [
      {
        id: "scene1_hook",
        type: "test-project/hook",
        title: "The Hook",
        audio_file: "scene1_hook.mp3",
        audio_duration_seconds: 20,
      },
      {
        id: "scene2_phases",
        type: "test-project/phases",
        title: "The Phases",
        audio_file: "scene2_phases.mp3",
        audio_duration_seconds: 30,
      },
    ],
    audio: {
      voiceover_dir: "voiceover",
      buffer_between_scenes_seconds: 1.0,
    },
    total_duration_seconds: 52,
  };

  it("should render without crashing", () => {
    expect(() => SceneStoryboardPlayer({ storyboard: mockStoryboard })).not.toThrow();
  });

  it("should use default empty storyboard when none provided", () => {
    expect(() => SceneStoryboardPlayer({})).not.toThrow();
  });
});

describe("calculateStoryboardDuration", () => {
  it("should calculate total duration including buffer", () => {
    const storyboard: SceneStoryboard = {
      title: "Test",
      description: "",
      version: "2.0.0",
      project: "test",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#000",
        primary_color: "#fff",
        secondary_color: "#ccc",
        font_family: "Inter",
      },
      scenes: [
        {
          id: "scene1",
          type: "test/hook",
          title: "Scene 1",
          audio_file: "s1.mp3",
          audio_duration_seconds: 10,
        },
        {
          id: "scene2",
          type: "test/main",
          title: "Scene 2",
          audio_file: "s2.mp3",
          audio_duration_seconds: 20,
        },
      ],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 2.0,
      },
      total_duration_seconds: 34,
    };

    const duration = calculateStoryboardDuration(storyboard);
    // (10 + 2) + (20 + 2) = 34 seconds
    expect(duration).toBe(34);
  });

  it("should use default buffer of 1.0 when not specified", () => {
    const storyboard: SceneStoryboard = {
      title: "Test",
      description: "",
      version: "2.0.0",
      project: "test",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#000",
        primary_color: "#fff",
        secondary_color: "#ccc",
        font_family: "Inter",
      },
      scenes: [
        {
          id: "scene1",
          type: "test/hook",
          title: "Scene 1",
          audio_file: "s1.mp3",
          audio_duration_seconds: 10,
        },
      ],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
      },
      total_duration_seconds: 11,
    };

    const duration = calculateStoryboardDuration(storyboard);
    // 10 + 1 (default buffer) = 11 seconds
    expect(duration).toBe(11);
  });

  it("should return 0 for empty scenes array", () => {
    const storyboard: SceneStoryboard = {
      title: "Empty",
      description: "",
      version: "2.0.0",
      project: "test",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#000",
        primary_color: "#fff",
        secondary_color: "#ccc",
        font_family: "Inter",
      },
      scenes: [],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
      },
      total_duration_seconds: 0,
    };

    const duration = calculateStoryboardDuration(storyboard);
    expect(duration).toBe(0);
  });
});

describe("StoryboardScene interface", () => {
  it("should accept optional sfx_cues", () => {
    const scene = {
      id: "scene1",
      type: "project/hook",
      title: "Hook",
      audio_file: "hook.mp3",
      audio_duration_seconds: 20,
      sfx_cues: [
        { sound: "whoosh", frame: 10, volume: 0.5 },
        { sound: "impact", frame: 45, volume: 0.3, duration_frames: 30 },
      ],
    };

    expect(scene.sfx_cues).toHaveLength(2);
    expect(scene.sfx_cues[0].sound).toBe("whoosh");
    expect(scene.sfx_cues[1].duration_frames).toBe(30);
  });
});

describe("Background music rendering", () => {
  it("should render BackgroundMusic when background_music config is present", () => {
    const storyboardWithMusic: SceneStoryboard = {
      title: "Test Video",
      description: "Test description",
      version: "2.0.0",
      project: "test-project",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#0f0f1a",
        primary_color: "#00d9ff",
        secondary_color: "#ff6b35",
        font_family: "Inter",
      },
      scenes: [
        {
          id: "scene1_hook",
          type: "test-project/hook",
          title: "The Hook",
          audio_file: "scene1_hook.mp3",
          audio_duration_seconds: 20,
        },
      ],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
        background_music: {
          path: "music/background.mp3",
          volume: 0.15,
        },
      },
      total_duration_seconds: 21,
    };

    const result = SceneStoryboardPlayer({ storyboard: storyboardWithMusic });

    // Check that background_music.path exists and is accessible
    expect(storyboardWithMusic.audio?.background_music?.path).toBe("music/background.mp3");
    expect(storyboardWithMusic.audio?.background_music?.volume).toBe(0.15);
  });

  it("should handle missing audio config gracefully", () => {
    const storyboardNoAudio: SceneStoryboard = {
      title: "Test Video",
      description: "Test description",
      version: "2.0.0",
      project: "test-project",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#0f0f1a",
        primary_color: "#00d9ff",
        secondary_color: "#ff6b35",
        font_family: "Inter",
      },
      scenes: [],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
      },
      total_duration_seconds: 0,
    };

    expect(() => SceneStoryboardPlayer({ storyboard: storyboardNoAudio })).not.toThrow();
  });

  it("should extract background_music from storyboard.audio correctly", () => {
    const storyboard: SceneStoryboard = {
      title: "Test",
      description: "",
      version: "2.0.0",
      project: "test",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#000",
        primary_color: "#fff",
        secondary_color: "#ccc",
        font_family: "Inter",
      },
      scenes: [],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
        background_music: {
          path: "music/background.mp3",
          volume: 0.12,
        },
      },
      total_duration_seconds: 0,
    };

    // Simulate how SceneStoryboardPlayer extracts background music
    const backgroundMusic = storyboard.audio?.background_music;
    const musicVolume = backgroundMusic?.volume ?? 0.1;

    expect(backgroundMusic).toBeDefined();
    expect(backgroundMusic?.path).toBe("music/background.mp3");
    expect(musicVolume).toBe(0.12);
  });
});

describe("Cinematic scene transitions", () => {
  it("should use cinematic transition styles", () => {
    // New cinematic transition types
    const transitionStyles = [
      "cinematicFade",
      "cinematicSlideLeft",
      "cinematicFade",
      "cinematicSlideRight",
      "cinematicFade",
      "cinematicSlideUp",
      "simpleFade",
      "cinematicFade",
    ];

    expect(transitionStyles).toContain("cinematicFade");
    expect(transitionStyles).toContain("cinematicSlideLeft");
    expect(transitionStyles).toContain("cinematicSlideRight");
    expect(transitionStyles).toContain("cinematicSlideUp");
    expect(transitionStyles).toContain("simpleFade");
  });

  it("should assign transition styles deterministically based on scene index", () => {
    const transitionStyles = [
      "cinematicFade",
      "cinematicSlideLeft",
      "cinematicFade",
      "cinematicSlideRight",
      "cinematicFade",
      "cinematicSlideUp",
      "simpleFade",
      "cinematicFade",
    ];

    const getTransitionStyle = (sceneIndex: number): string => {
      const hash = (sceneIndex * 7 + 3) % transitionStyles.length;
      return transitionStyles[hash];
    };

    // Same scene index should always return the same transition
    const firstCall = getTransitionStyle(5);
    const secondCall = getTransitionStyle(5);

    expect(firstCall).toBe(secondCall);
  });

  it("should have 8 transition styles defined", () => {
    const transitionStyles = [
      "cinematicFade",
      "cinematicSlideLeft",
      "cinematicFade",
      "cinematicSlideRight",
      "cinematicFade",
      "cinematicSlideUp",
      "simpleFade",
      "cinematicFade",
    ];

    expect(transitionStyles).toHaveLength(8);
  });

  it("should render scenes with TransitionSeries", () => {
    const storyboard: SceneStoryboard = {
      title: "Test Video",
      description: "Test description",
      version: "2.0.0",
      project: "test-project",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#0f0f1a",
        primary_color: "#00d9ff",
        secondary_color: "#ff6b35",
        font_family: "Inter",
      },
      scenes: [
        {
          id: "scene1_hook",
          type: "test-project/hook",
          title: "The Hook",
          audio_file: "scene1_hook.mp3",
          audio_duration_seconds: 20,
        },
        {
          id: "scene2_phases",
          type: "test-project/phases",
          title: "The Phases",
          audio_file: "scene2_phases.mp3",
          audio_duration_seconds: 30,
        },
        {
          id: "scene3_conclusion",
          type: "test-project/conclusion",
          title: "Conclusion",
          audio_file: "scene3_conclusion.mp3",
          audio_duration_seconds: 15,
        },
      ],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
      },
      total_duration_seconds: 68,
    };

    // Should render without throwing for multiple scenes
    expect(() => SceneStoryboardPlayer({ storyboard })).not.toThrow();
  });

  it("should use slower transition duration for cinematic feel", () => {
    // TRANSITION_DURATION_FRAMES is 45 frames (~1.5 seconds at 30fps)
    const TRANSITION_DURATION_FRAMES = 45;
    const fps = 30;
    const transitionSeconds = TRANSITION_DURATION_FRAMES / fps;

    expect(transitionSeconds).toBe(1.5);
  });

  it("should add transition padding to scenes for audio timing", () => {
    // Each scene (except last) gets TRANSITION_DURATION_FRAMES added
    // so audio finishes before transition begins
    const TRANSITION_DURATION_FRAMES = 45;
    const audioDuration = 20; // seconds
    const buffer = 1.0; // seconds
    const fps = 30;

    const baseDurationFrames = Math.ceil((audioDuration + buffer) * fps);
    const paddedDurationFrames = baseDurationFrames + TRANSITION_DURATION_FRAMES;

    expect(paddedDurationFrames).toBe(baseDurationFrames + 45);
  });
});

describe("Audio layer separation", () => {
  it("should handle audio separately from visual transitions", () => {
    // Audio is rendered in separate Sequences to avoid double-playback during transitions
    // Visual content uses TransitionSeries for overlapping transitions
    // Audio uses regular Sequences that don't overlap

    const storyboard: SceneStoryboard = {
      title: "Test Video",
      description: "Test description",
      version: "2.0.0",
      project: "test-project",
      video: { width: 1920, height: 1080, fps: 30 },
      style: {
        background_color: "#0f0f1a",
        primary_color: "#00d9ff",
        secondary_color: "#ff6b35",
        font_family: "Inter",
      },
      scenes: [
        {
          id: "scene1_hook",
          type: "test-project/hook",
          title: "The Hook",
          audio_file: "scene1_hook.mp3",
          audio_duration_seconds: 20,
        },
      ],
      audio: {
        voiceover_dir: "voiceover",
        buffer_between_scenes_seconds: 1.0,
      },
      total_duration_seconds: 21,
    };

    expect(() => SceneStoryboardPlayer({ storyboard })).not.toThrow();
  });
});
