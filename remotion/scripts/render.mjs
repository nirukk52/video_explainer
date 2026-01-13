#!/usr/bin/env node
/**
 * Render script for programmatic video generation.
 *
 * Usage:
 *   node scripts/render.mjs --project ../projects/llm-inference --output ./output.mp4
 *   node scripts/render.mjs --project ../projects/llm-inference --output ./output-4k.mp4 --width 3840 --height 2160
 *   node scripts/render.mjs --composition ScenePlayer --storyboard ./storyboard.json --output ./output.mp4
 *
 * The --project flag automatically finds storyboard.json and uses the project's
 * voiceover directory for audio files.
 *
 * Resolution options:
 *   --width <number>   Output width (default: 1920)
 *   --height <number>  Output height (default: 1080)
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";
import { readFileSync, existsSync } from "fs";
import os from "os";

import {
  parseArgs,
  calculateDuration,
  buildProps,
  validateConfig,
  deriveStoryboardPath,
  deriveProjectDir,
  getFinalResolution,
  validateSceneTypes,
} from "./render-utils.mjs";
import fs from "fs";
import path from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function main() {
  // Parse command line arguments
  const config = parseArgs(process.argv.slice(2));

  // Resolve project directory path
  if (config.projectDir) {
    config.projectDir = resolve(config.projectDir);
  }

  // If project dir is specified, derive storyboard path from it
  if (config.projectDir && !config.storyboardPath) {
    config.storyboardPath = resolve(config.projectDir, "storyboard/storyboard.json");
  }

  // Build props based on arguments
  let props;
  let projectDir = config.projectDir;

  if (config.storyboardPath) {
    // Scene-based storyboard (new format)
    if (!existsSync(config.storyboardPath)) {
      console.error(`Storyboard file not found: ${config.storyboardPath}`);
      process.exit(1);
    }

    const storyboard = JSON.parse(readFileSync(config.storyboardPath, "utf-8"));
    props = buildProps(storyboard, config.voiceoverBasePath);

    // Derive project directory from storyboard path if not specified
    if (!projectDir) {
      projectDir = resolve(dirname(config.storyboardPath), "..");
    }

    console.log(`Loaded storyboard from ${config.storyboardPath}`);
    console.log(`Project directory: ${projectDir}`);
    console.log(`Title: ${storyboard.title}`);
    console.log(`Scenes: ${storyboard.scenes.length}`);
    console.log(`Composition: ${config.compositionId}`);
  } else if (config.propsPath) {
    // Legacy props file
    if (!existsSync(config.propsPath)) {
      console.error(`Props file not found: ${config.propsPath}`);
      process.exit(1);
    }

    props = JSON.parse(readFileSync(config.propsPath, "utf-8"));
    console.log(`Loaded props from ${config.propsPath}`);
    console.log(`Composition: ${config.compositionId}`);
  } else {
    console.error("Usage:");
    console.error("  node scripts/render.mjs --composition ScenePlayer --storyboard <storyboard.json> --output <output.mp4>");
    console.error("  node scripts/render.mjs [--composition <id>] --props <props.json> --output <output.mp4>");
    process.exit(1);
  }

  // Validate project directory
  if (!projectDir) {
    console.error("Project directory is required for scene loading");
    process.exit(1);
  }

  const projectScenesDir = resolve(projectDir, "scenes");
  if (!existsSync(projectScenesDir)) {
    console.error(`Project scenes directory not found: ${projectScenesDir}`);
    process.exit(1);
  }

  // Validate scene types match registry keys
  if (config.storyboardPath) {
    const storyboard = JSON.parse(readFileSync(config.storyboardPath, "utf-8"));
    const validation = validateSceneTypes(storyboard, projectScenesDir, fs, path);

    if (validation.error) {
      console.error(`\n❌ Scene validation error: ${validation.error}`);
      process.exit(1);
    }

    if (!validation.valid) {
      console.error("\n❌ Scene type mismatch detected!");
      console.error("The following storyboard scene types don't match registry keys:\n");

      for (const mismatch of validation.mismatches) {
        console.error(`  Scene: ${mismatch.sceneId}`);
        console.error(`    Storyboard type: "${mismatch.storyboardType}"`);
        if (mismatch.suggestions.length > 0) {
          console.error(`    Did you mean: ${mismatch.suggestions.map(s => `"${s}"`).join(", ")}?`);
        }
        console.error("");
      }

      console.error("Available registry keys:", validation.registryKeys.join(", "));
      console.error("\nFix: Update scenes/index.ts registry keys to match storyboard scene types,");
      console.error("     or update storyboard.json scene types to match registry keys.");
      process.exit(1);
    }

    console.log("✓ Scene types validated successfully");
  }

  // Calculate total duration
  const totalDuration = calculateDuration(config.compositionId, props);
  console.log(`Total duration: ${totalDuration}s`);

  // Bundle the Remotion project
  console.log("\nBundling Remotion project...");
  const entryPoint = resolve(__dirname, "../src/index.ts");

  // Use project directory as public dir for assets (voiceover, music, sfx)
  const publicDir = projectDir;
  console.log(`Public directory: ${publicDir}`);
  console.log(`Project scenes: ${projectScenesDir}`);

  const bundleLocation = await bundle({
    entryPoint,
    publicDir,
    onProgress: (progress) => {
      if (progress % 20 === 0) {
        console.log(`  Bundle progress: ${progress}%`);
      }
    },
    // Configure webpack aliases for project scenes and shared components
    webpackOverride: (webpackConfig) => ({
      ...webpackConfig,
      resolve: {
        ...webpackConfig.resolve,
        alias: {
          ...webpackConfig.resolve?.alias,
          "@project-scenes": projectScenesDir,
          "@remotion-components": resolve(__dirname, "../src/components"),
        },
      },
    }),
  });

  console.log("Bundle created successfully");

  // Select the composition
  console.log("\nPreparing composition...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: config.compositionId,
    inputProps: props,
  });

  // Get final resolution
  const resolution = getFinalResolution(config.width, config.height, composition);

  console.log(`Composition: ${composition.id}`);
  console.log(`Duration: ${composition.durationInFrames} frames @ ${composition.fps}fps`);
  console.log(`Resolution: ${resolution.width}x${resolution.height}${resolution.isCustom ? " (custom)" : ""}`);

  // Render the video
  // Performance options - can be overridden via CLI flags
  const concurrency = config.concurrency || Math.max(4, Math.floor(os.cpus().length * 0.75));
  const x264Preset = config.fast ? "faster" : "medium"; // "faster" trades some quality for speed

  console.log(`\nRendering to ${config.outputPath}...`);
  console.log(`  Concurrency: ${concurrency} threads`);
  console.log(`  Encoding preset: ${x264Preset}`);

  await renderMedia({
    composition: {
      ...composition,
      width: resolution.width,
      height: resolution.height,
    },
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: config.outputPath,
    inputProps: props,
    concurrency,
    x264Preset,
    jpegQuality: config.fast ? 80 : 90, // Lower quality = faster frame generation
    onProgress: ({ progress }) => {
      const percent = Math.round(progress * 100);
      if (percent % 10 === 0) {
        process.stdout.write(`\r  Render progress: ${percent}%`);
      }
    },
  });

  console.log(`\n\nVideo rendered successfully: ${config.outputPath}`);
}

main().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});
