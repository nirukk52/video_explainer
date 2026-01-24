import { Composition } from "remotion";
import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { ExplainerVideo } from "./scenes/ExplainerVideo";
import { StoryboardPlayer } from "./scenes/StoryboardPlayer";
import { ThreeDemo } from "./ThreeDemo";
import { ShortsPlayer } from "./shorts/ShortsPlayer";
import type { ShortsStoryboard } from "./shorts/ShortsPlayer";
import { VarunPlayer, Script } from "./templates";

// Load fonts globally
loadOutfit(); // Modern geometric sans-serif for tech content
loadInter();  // Clean sans-serif for shorts captions
loadPlayfair(); // Serif font for Varun Mayya style headlines
import {
  SceneStoryboardPlayer,
  DynamicStoryboardPlayer,
  SceneStoryboard,
  calculateStoryboardDuration,
} from "./scenes/SceneStoryboardPlayer";
import {
  SingleScenePlayer,
  SingleScenePlayerProps,
  calculateSingleSceneDuration,
} from "./scenes/SingleScenePlayer";
import { defaultScriptProps } from "./types/script";
import type { Storyboard } from "./types/storyboard";

// Scene registry - used for data-driven rendering
import { getAllScenePaths } from "./scenes/index";

// Default beat-based storyboard for preview (old format)
const defaultStoryboard: Storyboard = {
  id: "preview",
  title: "Storyboard Preview",
  duration_seconds: 10,
  beats: [
    {
      id: "test",
      start_seconds: 0,
      end_seconds: 10,
      voiceover: "This is a test storyboard.",
      elements: [
        {
          id: "test_tokens",
          component: "token_row",
          props: {
            tokens: ["Hello", "World"],
            mode: "prefill",
            label: "TEST",
          },
          position: { x: "center", y: "center" },
          animations: [
            { action: "activate_all", at_seconds: 2, duration_seconds: 0.5 },
          ],
        },
      ],
    },
  ],
};

/**
 * Root component that registers all compositions.
 * Each composition can be rendered independently.
 *
 * The main composition is ScenePlayer which dynamically loads scenes
 * from the project specified via the @project-scenes webpack alias.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ===== Data-Driven Video Player ===== */}

      {/* Scene Storyboard Player - dynamically loads project's storyboard.json */}
      {/* Run with: PROJECT=your-project npm run dev */}
      <Composition
        id="ScenePlayer"
        component={DynamicStoryboardPlayer}
        durationInFrames={30 * 1800} // 30 min max - actual duration set by storyboard
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          voiceoverBasePath: "voiceover",
        }}
        calculateMetadata={async ({ props }) => {
          // When storyboard is provided (e.g., during render), use its duration
          const storyboard = props.storyboard as SceneStoryboard | undefined;
          if (storyboard) {
            const duration = calculateStoryboardDuration(storyboard);
            return {
              durationInFrames: Math.ceil(duration * 30),
            };
          }
          // For dynamic loading (dev preview), try to get injected storyboard
          try {
            const injected = process.env.__STORYBOARD_JSON__;
            if (injected && typeof injected === "object") {
              const duration = calculateStoryboardDuration(injected as unknown as SceneStoryboard);
              return {
                durationInFrames: Math.ceil(duration * 30),
              };
            }
          } catch {
            // Fallback to default
          }
          // Fallback for dev preview without storyboard
          return {
            durationInFrames: 30 * 1800, // 30 min max
          };
        }}
      />

      {/* ===== Single Scene Player (for inspection/refinement) ===== */}

      {/* Single Scene Player - loads just ONE scene starting at frame 0 */}
      {/* Perfect for visual inspection without navigating through entire video */}
      {/* URL: /SingleScenePlayer?props={"sceneType":"project/scene_name","durationInSeconds":30} */}
      <Composition
        id="SingleScenePlayer"
        component={SingleScenePlayer}
        durationInFrames={30 * 60} // Default 1 min, overridden by calculateMetadata
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          sceneType: "unknown",
          durationInSeconds: 60,
          voiceoverBasePath: "voiceover",
          backgroundColor: "#0f0f1a",
        }}
        calculateMetadata={async ({ props }) => {
          let duration = (props as SingleScenePlayerProps).durationInSeconds || 60;

          // In browser context (Studio), try to read from URL directly
          if (typeof window !== "undefined") {
            try {
              const params = new URLSearchParams(window.location.search);
              const propsJson = params.get("props");
              if (propsJson) {
                const parsed = JSON.parse(propsJson);
                if (parsed.durationInSeconds) {
                  duration = parsed.durationInSeconds;
                  console.log("[calculateMetadata] Got duration from URL:", duration);
                }
              }
            } catch (e) {
              console.warn("[calculateMetadata] Failed to parse URL props:", e);
            }
          }

          return {
            durationInFrames: Math.ceil(duration * 30),
          };
        }}
      />

      {/* ===== YouTube Shorts (Vertical 9:16) ===== */}

      {/* Vertical Scene Player for YouTube Shorts */}
      {/* Run with: PROJECT=your-project VARIANT=variant-name npm run dev:short */}
      <Composition
        id="VerticalScenePlayer"
        component={DynamicStoryboardPlayer}
        durationInFrames={30 * 60} // 1 min max for shorts
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          voiceoverBasePath: "voiceover",
          isVertical: true,
        }}
        calculateMetadata={async ({ props }) => {
          // When storyboard is provided (e.g., during render), use its duration
          const storyboard = props.storyboard as SceneStoryboard | undefined;
          if (storyboard) {
            const duration = calculateStoryboardDuration(storyboard);
            return {
              durationInFrames: Math.ceil(duration * 30),
            };
          }
          // For dynamic loading (dev preview), try to get injected storyboard
          try {
            const injected = process.env.__STORYBOARD_JSON__;
            if (injected && typeof injected === "object") {
              const duration = calculateStoryboardDuration(injected as unknown as SceneStoryboard);
              return {
                durationInFrames: Math.ceil(duration * 30),
              };
            }
          } catch {
            // Fallback to default
          }
          // Fallback for dev preview without storyboard
          return {
            durationInFrames: 30 * 60, // 1 min max for shorts
          };
        }}
      />

      {/* Shorts Player - Optimized for YouTube Shorts / TikTok / Reels */}
      {/* Uses simplified visuals + animated captions */}
      {/* Run with: PROJECT=your-project npm run dev (loads shorts_storyboard.json) */}
      {/* Or: PROJECT=your-project VARIANT=variant-name npm run dev */}
      <Composition
        id="ShortsPlayer"
        component={ShortsPlayer}
        durationInFrames={30 * 60} // 1 min max
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          storyboard: {
            id: "preview",
            title: "Shorts Preview",
            total_duration_seconds: 10,
            beats: [
              {
                id: "beat1",
                start_seconds: 0,
                end_seconds: 5,
                visual: {
                  type: "big_number",
                  primary_text: "150,528",
                  secondary_text: "pixels in one image",
                  color: "primary",
                },
                caption_text: "One image contains over 150 thousand pixels",
                word_timestamps: [],
              },
              {
                id: "beat2",
                start_seconds: 5,
                end_seconds: 10,
                visual: {
                  type: "question",
                  primary_text: "How do transformers handle this?",
                  color: "accent",
                },
                caption_text: "But how do transformers actually handle this?",
                word_timestamps: [],
              },
            ],
            hook_question: "How do transformers process images?",
            cta_text: "Full breakdown in description",
          } as ShortsStoryboard,
        }}
        calculateMetadata={async ({ props }) => {
          // Try to use injected shorts storyboard from PROJECT env
          try {
            const injected = process.env.__SHORTS_STORYBOARD_JSON__;
            if (injected && typeof injected === "object") {
              const storyboard = injected as unknown as ShortsStoryboard;
              return {
                durationInFrames: Math.ceil(storyboard.total_duration_seconds * 30),
                props: { ...props, storyboard },
              };
            }
          } catch {
            // Fallback to props
          }
          const storyboard = props.storyboard as ShortsStoryboard | undefined;
          const duration = storyboard?.total_duration_seconds || 60;
          return {
            durationInFrames: Math.ceil(duration * 30),
          };
        }}
      />

      {/* ===== Varun Mayya Style Shorts ===== */}
      
      {/* VarunPlayer - JSON-driven template system for Varun Mayya style */}
      {/* Templates: SplitVideo, VideoCard, TextOverProof, FullAvatar, etc. */}
      <Composition
        id="VarunPlayer"
        component={VarunPlayer}
        durationInFrames={30 * 60} // 1 min max
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          script: {
            id: "preview",
            title: "Varun Style Preview",
            duration_seconds: 4,
            scenes: [
              {
                id: "scene_001",
                template: "VideoCard",
                start_seconds: 0,
                end_seconds: 4,
                background: { type: "solid", color: "#000000" },
                video_inset: {
                  src: "backgrounds/placeholder.mp4",
                  position: "center",
                  width_percent: 85,
                  border_radius: 16,
                },
                avatar: { visible: false },
                text: {
                  headline: {
                    lines: [
                      { text: "looks like", style: "normal" },
                      { text: "something", style: "italic" },
                      { text: "straight out of a", style: "normal" },
                    ],
                  },
                  position: "top",
                },
              },
            ],
          } as Script,
        }}
        calculateMetadata={async ({ props }) => {
          // Try to use injected script from PROJECT env
          try {
            const injected = process.env.__VARUN_SCRIPT_JSON__;
            if (injected && typeof injected === "object") {
              const script = injected as unknown as Script;
              return {
                durationInFrames: Math.ceil(script.duration_seconds * 30),
                props: { ...props, script },
              };
            }
          } catch {
            // Fallback to props
          }
          const script = props.script as Script | undefined;
          const duration = script?.duration_seconds || 60;
          return {
            durationInFrames: Math.ceil(duration * 30),
          };
        }}
      />

      {/* ===== Legacy Compositions (for backwards compatibility) ===== */}

      {/* Main explainer video composition */}
      <Composition
        id="ExplainerVideo"
        component={ExplainerVideo}
        durationInFrames={30 * 180}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultScriptProps}
        calculateMetadata={async ({ props }) => {
          const totalDuration = props.scenes.reduce(
            (acc, scene) => acc + scene.durationInSeconds,
            0
          );
          return {
            durationInFrames: Math.ceil(totalDuration * 30),
          };
        }}
      />

      {/* Beat-based Storyboard Player (old format) */}
      <Composition
        id="StoryboardPlayer"
        component={StoryboardPlayer}
        durationInFrames={30 * 60}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          storyboard: defaultStoryboard,
        }}
        calculateMetadata={async ({ props }) => {
          const storyboard = props.storyboard as Storyboard | undefined;
          const duration = storyboard?.duration_seconds || 60;
          return {
            durationInFrames: Math.ceil(duration * 30),
          };
        }}
      />

      {/* ===== Demo Compositions ===== */}

      {/* Three.js Demo - showcases 3D capabilities */}
      <Composition
        id="ThreeDemo"
        component={ThreeDemo}
        durationInFrames={30 * 10}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
