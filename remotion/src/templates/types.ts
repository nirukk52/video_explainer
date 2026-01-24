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
  type: 'screenshot' | 'video' | 'gradient' | 'solid' | 'stock';
  src?: string;
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
}

/** Video inset for VideoCard template */
export interface VideoInset {
  src: string;
  position: 'center' | 'top' | 'bottom';
  width_percent: number;
  border_radius?: number;
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
  | 'VideoCard';

/** Scene definition - matches JSON schema */
export interface Scene {
  id: string;
  template: TemplateType;
  start_seconds: number;
  end_seconds: number;
  audio?: SceneAudio;
  background?: SceneBackground;
  avatar?: SceneAvatar;
  video_inset?: VideoInset;
  text?: SceneText;
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
