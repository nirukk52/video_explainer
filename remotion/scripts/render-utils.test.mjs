/**
 * Tests for render utility functions.
 */

import { describe, it, expect } from "vitest";

import {
  parseArgs,
  calculateDuration,
  buildProps,
  validateConfig,
  deriveStoryboardPath,
  deriveProjectDir,
  getFinalResolution,
  RESOLUTION_PRESETS,
} from "./render-utils.mjs";

describe("parseArgs", () => {
  it("should return default values for empty args", () => {
    const config = parseArgs([]);
    expect(config.propsPath).toBeNull();
    expect(config.storyboardPath).toBeNull();
    expect(config.projectDir).toBeNull();
    expect(config.outputPath).toBe("./output.mp4");
    expect(config.compositionId).toBe("ScenePlayer");
    expect(config.voiceoverBasePath).toBe("voiceover");
    expect(config.width).toBeNull();
    expect(config.height).toBeNull();
    expect(config.concurrency).toBeNull();
    expect(config.fast).toBe(false);
  });

  it("should parse --project flag", () => {
    const config = parseArgs(["--project", "/path/to/project"]);
    expect(config.projectDir).toBe("/path/to/project");
  });

  it("should parse --storyboard flag", () => {
    const config = parseArgs(["--storyboard", "/path/to/storyboard.json"]);
    expect(config.storyboardPath).toBe("/path/to/storyboard.json");
  });

  it("should parse --props flag", () => {
    const config = parseArgs(["--props", "/path/to/props.json"]);
    expect(config.propsPath).toBe("/path/to/props.json");
  });

  it("should parse --output flag", () => {
    const config = parseArgs(["--output", "/output/video.mp4"]);
    expect(config.outputPath).toBe("/output/video.mp4");
  });

  it("should parse --composition flag", () => {
    const config = parseArgs(["--composition", "StoryboardPlayer"]);
    expect(config.compositionId).toBe("StoryboardPlayer");
  });

  it("should parse --voiceover-path flag", () => {
    const config = parseArgs(["--voiceover-path", "audio/voiceovers"]);
    expect(config.voiceoverBasePath).toBe("audio/voiceovers");
  });

  it("should parse --width flag", () => {
    const config = parseArgs(["--width", "3840"]);
    expect(config.width).toBe(3840);
  });

  it("should parse --height flag", () => {
    const config = parseArgs(["--height", "2160"]);
    expect(config.height).toBe(2160);
  });

  it("should parse multiple flags together", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--output", "/output/test.mp4",
      "--width", "1920",
      "--height", "1080",
      "--composition", "MyComp",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.outputPath).toBe("/output/test.mp4");
    expect(config.width).toBe(1920);
    expect(config.height).toBe(1080);
    expect(config.compositionId).toBe("MyComp");
  });

  it("should ignore flags without values", () => {
    const config = parseArgs(["--width"]);
    expect(config.width).toBeNull();
  });

  it("should parse 4K resolution correctly", () => {
    const config = parseArgs(["--width", "3840", "--height", "2160"]);
    expect(config.width).toBe(3840);
    expect(config.height).toBe(2160);
  });

  it("should parse --fast flag", () => {
    const config = parseArgs(["--fast"]);
    expect(config.fast).toBe(true);
  });

  it("should parse --concurrency flag", () => {
    const config = parseArgs(["--concurrency", "8"]);
    expect(config.concurrency).toBe(8);
  });

  it("should parse --concurrency with different values", () => {
    const config = parseArgs(["--concurrency", "16"]);
    expect(config.concurrency).toBe(16);
  });

  it("should handle --fast with other flags", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--fast",
      "--output", "/output/test.mp4",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.fast).toBe(true);
    expect(config.outputPath).toBe("/output/test.mp4");
  });

  it("should handle --concurrency with other flags", () => {
    const config = parseArgs([
      "--project", "/projects/test",
      "--concurrency", "12",
      "--fast",
    ]);
    expect(config.projectDir).toBe("/projects/test");
    expect(config.concurrency).toBe(12);
    expect(config.fast).toBe(true);
  });

  it("should ignore --concurrency without value", () => {
    const config = parseArgs(["--concurrency"]);
    expect(config.concurrency).toBeNull();
  });
});

describe("calculateDuration", () => {
  it("should calculate duration for ScenePlayer with storyboard", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 15 },
          { audio_duration_seconds: 5 },
        ],
        audio: { buffer_between_scenes_seconds: 1.0 },
      },
    };
    // 10 + 1 + 15 + 1 + 5 + 1 = 33
    expect(calculateDuration("ScenePlayer", props)).toBe(33);
  });

  it("should use default buffer of 1.0 when not specified", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 20 },
        ],
      },
    };
    // 10 + 1 + 20 + 1 = 32
    expect(calculateDuration("ScenePlayer", props)).toBe(32);
  });

  it("should calculate duration for StoryboardPlayer", () => {
    const props = {
      storyboard: {
        duration_seconds: 120,
        beats: [],
      },
    };
    expect(calculateDuration("StoryboardPlayer", props)).toBe(120);
  });

  it("should calculate duration for legacy scenes format", () => {
    const props = {
      scenes: [
        { durationInSeconds: 30 },
        { durationInSeconds: 45 },
        { durationInSeconds: 15 },
      ],
    };
    expect(calculateDuration("LegacyPlayer", props)).toBe(90);
  });

  it("should use duration_seconds fallback", () => {
    const props = {
      duration_seconds: 180,
    };
    expect(calculateDuration("UnknownComp", props)).toBe(180);
  });

  it("should default to 60 seconds", () => {
    const props = {};
    expect(calculateDuration("UnknownComp", props)).toBe(60);
  });

  it("should handle empty scenes array", () => {
    const props = {
      storyboard: {
        scenes: [],
      },
    };
    expect(calculateDuration("ScenePlayer", props)).toBe(0);
  });

  it("should handle custom buffer value", () => {
    const props = {
      storyboard: {
        scenes: [
          { audio_duration_seconds: 10 },
          { audio_duration_seconds: 10 },
        ],
        audio: { buffer_between_scenes_seconds: 2.0 },
      },
    };
    // 10 + 2 + 10 + 2 = 24
    expect(calculateDuration("ScenePlayer", props)).toBe(24);
  });
});

describe("buildProps", () => {
  it("should create props object with storyboard and voiceover path", () => {
    const storyboard = { title: "Test", scenes: [] };
    const voiceoverBasePath = "voiceover";

    const props = buildProps(storyboard, voiceoverBasePath);

    expect(props.storyboard).toBe(storyboard);
    expect(props.voiceoverBasePath).toBe(voiceoverBasePath);
  });

  it("should preserve storyboard data", () => {
    const storyboard = {
      title: "My Video",
      scenes: [{ scene_id: "scene1" }, { scene_id: "scene2" }],
    };

    const props = buildProps(storyboard, "audio");

    expect(props.storyboard.title).toBe("My Video");
    expect(props.storyboard.scenes).toHaveLength(2);
  });
});

describe("validateConfig", () => {
  it("should be valid with storyboardPath", () => {
    const config = { storyboardPath: "/path/to/storyboard.json" };
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should be valid with propsPath", () => {
    const config = { propsPath: "/path/to/props.json" };
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should be invalid without storyboardPath or propsPath", () => {
    const config = {};
    const result = validateConfig(config);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("required");
  });

  it("should be valid with both paths", () => {
    const config = {
      storyboardPath: "/path/to/storyboard.json",
      propsPath: "/path/to/props.json",
    };
    expect(validateConfig(config).valid).toBe(true);
  });
});

describe("deriveStoryboardPath", () => {
  it("should append storyboard/storyboard.json to project dir", () => {
    const result = deriveStoryboardPath("/projects/my-video");
    expect(result).toBe("/projects/my-video/storyboard/storyboard.json");
  });

  it("should handle trailing slash", () => {
    const result = deriveStoryboardPath("/projects/my-video/");
    expect(result).toBe("/projects/my-video//storyboard/storyboard.json");
  });
});

describe("deriveProjectDir", () => {
  it("should derive project dir from storyboard path", () => {
    const result = deriveProjectDir("/projects/my-video/storyboard/storyboard.json");
    expect(result).toBe("/projects/my-video");
  });

  it("should handle relative paths", () => {
    const result = deriveProjectDir("projects/test/storyboard/storyboard.json");
    expect(result).toBe("projects/test");
  });
});

describe("getFinalResolution", () => {
  const mockComposition = { width: 1920, height: 1080 };

  it("should use composition dimensions when no custom dimensions", () => {
    const result = getFinalResolution(null, null, mockComposition);
    expect(result.width).toBe(1920);
    expect(result.height).toBe(1080);
    expect(result.isCustom).toBe(false);
  });

  it("should use custom width when provided", () => {
    const result = getFinalResolution(3840, null, mockComposition);
    expect(result.width).toBe(3840);
    expect(result.height).toBe(1080);
    expect(result.isCustom).toBe(true);
  });

  it("should use custom height when provided", () => {
    const result = getFinalResolution(null, 2160, mockComposition);
    expect(result.width).toBe(1920);
    expect(result.height).toBe(2160);
    expect(result.isCustom).toBe(true);
  });

  it("should use both custom dimensions when provided", () => {
    const result = getFinalResolution(3840, 2160, mockComposition);
    expect(result.width).toBe(3840);
    expect(result.height).toBe(2160);
    expect(result.isCustom).toBe(true);
  });

  it("should mark as custom when only width is changed", () => {
    const result = getFinalResolution(1280, null, mockComposition);
    expect(result.isCustom).toBe(true);
  });
});

describe("RESOLUTION_PRESETS", () => {
  it("should have 4k preset", () => {
    expect(RESOLUTION_PRESETS["4k"]).toEqual({ width: 3840, height: 2160 });
  });

  it("should have 1440p preset", () => {
    expect(RESOLUTION_PRESETS["1440p"]).toEqual({ width: 2560, height: 1440 });
  });

  it("should have 1080p preset", () => {
    expect(RESOLUTION_PRESETS["1080p"]).toEqual({ width: 1920, height: 1080 });
  });

  it("should have 720p preset", () => {
    expect(RESOLUTION_PRESETS["720p"]).toEqual({ width: 1280, height: 720 });
  });

  it("should have 480p preset", () => {
    expect(RESOLUTION_PRESETS["480p"]).toEqual({ width: 854, height: 480 });
  });

  it("should have 5 presets total", () => {
    expect(Object.keys(RESOLUTION_PRESETS)).toHaveLength(5);
  });

  it("should all maintain approximately 16:9 aspect ratio", () => {
    for (const [name, { width, height }] of Object.entries(RESOLUTION_PRESETS)) {
      const ratio = width / height;
      expect(Math.abs(ratio - 16/9)).toBeLessThan(0.01);
    }
  });
});

describe("Integration: Full argument parsing scenarios", () => {
  it("should handle typical 4K render command", () => {
    const config = parseArgs([
      "--project", "../projects/llm-inference",
      "--output", "./output-4k.mp4",
      "--width", "3840",
      "--height", "2160",
    ]);

    expect(config.projectDir).toBe("../projects/llm-inference");
    expect(config.outputPath).toBe("./output-4k.mp4");
    expect(config.width).toBe(3840);
    expect(config.height).toBe(2160);
  });

  it("should handle storyboard-only render", () => {
    const config = parseArgs([
      "--storyboard", "./storyboard.json",
      "--output", "./video.mp4",
    ]);

    expect(config.storyboardPath).toBe("./storyboard.json");
    expect(config.projectDir).toBeNull();
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should handle legacy props render", () => {
    const config = parseArgs([
      "--composition", "StoryboardPlayer",
      "--props", "./props.json",
      "--output", "./legacy.mp4",
    ]);

    expect(config.compositionId).toBe("StoryboardPlayer");
    expect(config.propsPath).toBe("./props.json");
    expect(validateConfig(config).valid).toBe(true);
  });

  it("should handle fast render with concurrency", () => {
    const config = parseArgs([
      "--project", "../projects/test",
      "--output", "./fast-render.mp4",
      "--fast",
      "--concurrency", "8",
    ]);

    expect(config.projectDir).toBe("../projects/test");
    expect(config.outputPath).toBe("./fast-render.mp4");
    expect(config.fast).toBe(true);
    expect(config.concurrency).toBe(8);
  });
});
