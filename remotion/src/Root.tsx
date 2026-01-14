import { Composition } from "remotion";
import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { ExplainerVideo } from "./scenes/ExplainerVideo";
import { StoryboardPlayer } from "./scenes/StoryboardPlayer";

// Load Outfit font globally - modern geometric sans-serif for tech content
loadOutfit();
import {
  SceneStoryboardPlayer,
  DynamicStoryboardPlayer,
  SceneStoryboard,
  calculateStoryboardDuration,
} from "./scenes/SceneStoryboardPlayer";
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
    </>
  );
};
