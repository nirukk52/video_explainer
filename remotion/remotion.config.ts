import { Config } from "@remotion/cli/config";
import path from "path";
import fs from "fs";
import webpack from "webpack";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer("angle");

// Get project name from environment variable, default to llm-image-understanding
const projectName = process.env.PROJECT || "llm-image-understanding";
// Get short variant from environment variable, default to "default"
const shortVariant = process.env.VARIANT || "default";

// Use process.cwd() which is the remotion directory when running npm run dev
const remotionDir = process.cwd();
const projectDir = path.resolve(remotionDir, `../projects/${projectName}`);
const projectScenesDir = path.resolve(projectDir, "scenes");
const shortScenesDir = path.resolve(projectDir, `short/${shortVariant}/scenes`);
const storyboardPath = path.resolve(projectDir, "storyboard/storyboard.json");
const shortsStoryboardPath = path.resolve(projectDir, `short/${shortVariant}/storyboard/shorts_storyboard.json`);

console.log(`[remotion.config] Project: ${projectName}`);
console.log(`[remotion.config] Project dir: ${projectDir}`);
console.log(`[remotion.config] Short variant: ${shortVariant}`);

// Load storyboard.json at build time for dev preview
let storyboardJson = "null";
if (fs.existsSync(storyboardPath)) {
  storyboardJson = fs.readFileSync(storyboardPath, "utf-8");
  console.log(`[remotion.config] Loaded storyboard.json`);
} else {
  console.warn(`[remotion.config] Warning: storyboard.json not found at ${storyboardPath}`);
}

// Load shorts storyboard at build time for dev preview
let shortsStoryboardJson = "null";
if (fs.existsSync(shortsStoryboardPath)) {
  shortsStoryboardJson = fs.readFileSync(shortsStoryboardPath, "utf-8");
  console.log(`[remotion.config] Loaded shorts_storyboard.json (variant: ${shortVariant})`);
} else {
  console.warn(`[remotion.config] Warning: shorts_storyboard.json not found at ${shortsStoryboardPath}`);
}

// Load Varun-style script.json at build time
const varunScriptPath = path.resolve(projectDir, "script/script.json");
let varunScriptJson = "null";
if (fs.existsSync(varunScriptPath)) {
  varunScriptJson = fs.readFileSync(varunScriptPath, "utf-8");
  console.log(`[remotion.config] Loaded script.json for VarunPlayer`);
} else {
  console.warn(`[remotion.config] Warning: script.json not found at ${varunScriptPath}`);
}

// Set public directory to project directory for assets (voiceover, music, sfx)
Config.setPublicDir(projectDir);

// Configure webpack alias for @project-scenes and inject storyboard
Config.overrideWebpackConfig((config) => {
  return {
    ...config,
    resolve: {
      ...config.resolve,
      alias: {
        ...config.resolve?.alias,
        "@project-scenes": projectScenesDir,
        "@project-short-scenes": shortScenesDir,
        "@remotion-components": path.resolve(remotionDir, "src/components"),
      },
      // Include remotion node_modules for project scene resolution
      modules: [
        ...(config.resolve?.modules || []),
        path.resolve(remotionDir, "node_modules"),
        "node_modules",
      ],
    },
    plugins: [
      ...(config.plugins || []),
      // Inject storyboards as global variables for dev preview
      new webpack.DefinePlugin({
        "process.env.__STORYBOARD_JSON__": storyboardJson,
        "process.env.__SHORTS_STORYBOARD_JSON__": shortsStoryboardJson,
        "process.env.__VARUN_SCRIPT_JSON__": varunScriptJson,
      }),
    ],
  };
});
