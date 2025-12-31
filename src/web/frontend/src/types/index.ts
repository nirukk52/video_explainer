// Project types
export interface ProjectSummary {
  id: string;
  title: string;
  description: string;
  has_narrations: boolean;
  has_voiceovers: boolean;
  has_storyboard: boolean;
  has_render: boolean;
}

export interface VideoSettings {
  width: number;
  height: number;
  fps: number;
  target_duration_seconds: number;
}

export interface TTSSettings {
  provider: string;
  voice_id: string;
}

export interface StyleSettings {
  background_color: string;
  primary_color: string;
  secondary_color: string;
  font_family: string;
}

export interface FileStatus {
  narrations_count: number;
  voiceover_count: number;
  has_storyboard: boolean;
  rendered_videos: string[];
  has_sfx: boolean;
}

export interface ProjectDetail {
  id: string;
  title: string;
  description: string;
  version: string;
  video: VideoSettings;
  tts: TTSSettings;
  style: StyleSettings;
  files: FileStatus;
}

// Narration types
export interface Narration {
  scene_id: string;
  title: string;
  duration_seconds: number;
  narration: string;
}

// Job types
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type JobType = 'voiceover' | 'render' | 'feedback' | 'sound';

export interface Job {
  job_id: string;
  type: JobType;
  project_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message: string;
}

// Voiceover types
export interface VoiceoverFile {
  scene_id: string;
  path: string;
  exists: boolean;
  duration_seconds: number | null;
}

// Render types
export interface RenderInfo {
  filename: string;
  path: string;
  size_bytes: number;
  is_preview: boolean;
}

// Feedback types
export interface FeedbackItem {
  id: string;
  feedback_text: string;
  status: string;
  scope: string | null;
  affected_scenes: string[];
  interpretation: string | null;
  files_modified: string[];
  error_message: string | null;
  timestamp: string;
}

// Sound types
export interface SoundInfo {
  name: string;
  description: string;
  exists: boolean;
}

// Storyboard types
export interface StoryboardScene {
  id: string;
  title: string;
  audio_duration_seconds: number;
  [key: string]: unknown;
}

export interface Storyboard {
  scenes: StoryboardScene[];
  total_duration_seconds: number;
  [key: string]: unknown;
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'job_update' | 'subscribe' | 'unsubscribe';
  job?: Job;
  project_id?: string;
}
