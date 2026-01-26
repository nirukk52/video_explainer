/**
 * Type definitions for Varun Mayya style shorts templates.
 * 
 * These types mirror the JSON schema in templates/schema.json
 * and define the props that each template component receives.
 */

/** Word timestamp for audio sync */
export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

/** Audio configuration for a scene */
export interface SceneAudio {
  text: string;
  file?: string;
  start_seconds?: number;
  word_timestamps?: WordTimestamp[];
}

/** Background configuration */
export interface SceneBackground {
  type: 'screenshot' | 'video' | 'ai_video' | 'gradient' | 'solid' | 'stock';
  src?: string;
  prompt?: string;
  color?: string;
  colors?: string[];
  position?: 'top' | 'center' | 'bottom';
  height_percent?: number;
  crop?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  highlight_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

/** Avatar configuration */
export interface SceneAvatar {
  visible: boolean;
  position?: 'full' | 'bottom' | 'pip_corner' | 'off';
  src?: string;
  height_percent?: number;
  /** When true, extract and use audio from avatar video even if avatar is not visible */
  use_avatar_audio?: boolean;
}

/** Video inset for VideoCard template */
export interface VideoInset {
  src: string;
  position: 'center' | 'top' | 'bottom';
  width_percent: number;
  height_multiplier?: number;
  border_radius?: number;
  border_width?: number;
  border_color?: string;
}

/** Text line with style */
export interface TextLine {
  text: string;
  style: 'normal' | 'italic' | 'bold';
}

/** Text configuration */
export interface SceneText {
  headline?: string | { lines: TextLine[] };
  caption_style?: 'word_by_word' | 'sentence';
  position?: 'top' | 'center' | 'bottom' | 'video_overlay_bottom';
  highlight_words?: string[];
  highlight_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  style?: 'normal' | 'dramatic';
  animate?: 'word_by_word' | 'fade_in';
}

/** Template types */
export type TemplateType = 
  | 'SplitProof' 
  | 'SplitVideo' 
  | 'TextOverProof' 
  | 'FullAvatar' 
  | 'ProofOnly' 
  | 'TextCard' 
  | 'VideoCard'
  | 'composite';

/** Word range for word_groups */
export interface WordRange {
  start: number;
  end: number;
}

/** Word group - a segment of a scene with its own template */
export interface WordGroup {
  id: string;
  template: Exclude<TemplateType, 'composite'>;
  word_range: WordRange;
  start_seconds: number;
  end_seconds: number;
  background?: SceneBackground & { prompt?: string };
  avatar?: SceneAvatar;
  video_inset?: VideoInset;
  text?: SceneText;
}

/** Audio file entry for composite scenes with multiple audio files */
export interface AudioFile {
  file: string;
  start_offset: number;
  duration_seconds: number;
}

/** Extended audio for composite scenes */
export interface CompositeSceneAudio extends SceneAudio {
  files?: AudioFile[];
}

/** Scene definition - matches JSON schema */
export interface Scene {
  id: string;
  template: TemplateType;
  start_seconds: number;
  end_seconds: number;
  audio?: SceneAudio | CompositeSceneAudio;
  background?: SceneBackground;
  avatar?: SceneAvatar;
  video_inset?: VideoInset;
  text?: SceneText;
  word_groups?: WordGroup[];
}

/** Full script definition */
export interface Script {
  id: string;
  title?: string;
  duration_seconds: number;
  scenes: Scene[];
}

/** Layout constants for 1080x1920 vertical format */
export const LAYOUT = {
  width: 1080,
  height: 1920,
  fps: 30,
} as const;

/** Color palette - Varun Mayya style */
export const COLORS = {
  background: '#000000',
  text: '#ffffff',
  textMuted: '#a0a0a0',
  accent: '#ffffff',
} as const;

/** Font settings - serif for headlines, sans for captions */
export const FONTS = {
  headline: '"Playfair Display", Georgia, serif',
  caption: '"Inter", -apple-system, sans-serif',
} as const;
