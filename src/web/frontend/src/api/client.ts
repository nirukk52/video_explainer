import type {
  ProjectSummary,
  ProjectDetail,
  Narration,
  Job,
  JobResponse,
  VoiceoverFile,
  RenderInfo,
  FeedbackItem,
  SoundInfo,
  Storyboard,
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    // Handle FastAPI validation errors (detail is an array) and regular errors (detail is a string)
    let message: string;
    if (Array.isArray(error.detail)) {
      // Pydantic validation error format
      message = error.detail.map((e: { loc?: string[]; msg?: string }) =>
        e.msg || 'Validation error'
      ).join(', ');
    } else {
      message = error.detail || `HTTP ${response.status}`;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Projects API
export const projectsApi = {
  list: () => fetchJson<ProjectSummary[]>(`${API_BASE}/projects`),

  get: (id: string) => fetchJson<ProjectDetail>(`${API_BASE}/projects/${id}`),

  create: (id: string, title: string, description = '') =>
    fetchJson<ProjectDetail>(`${API_BASE}/projects`, {
      method: 'POST',
      body: JSON.stringify({ id, title, description }),
    }),

  delete: (id: string) =>
    fetchJson<void>(`${API_BASE}/projects/${id}`, { method: 'DELETE' }),
};

// Narrations API
export const narrationsApi = {
  list: (projectId: string) =>
    fetchJson<Narration[]>(`${API_BASE}/projects/${projectId}/narrations`),

  get: (projectId: string, sceneId: string) =>
    fetchJson<Narration>(`${API_BASE}/projects/${projectId}/narrations/${sceneId}`),

  add: (projectId: string, narration: Partial<Narration>) =>
    fetchJson<Narration>(`${API_BASE}/projects/${projectId}/narrations`, {
      method: 'POST',
      body: JSON.stringify(narration),
    }),

  update: (projectId: string, sceneId: string, data: Partial<Narration>) =>
    fetchJson<Narration>(`${API_BASE}/projects/${projectId}/narrations/${sceneId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (projectId: string, sceneId: string) =>
    fetchJson<void>(`${API_BASE}/projects/${projectId}/narrations/${sceneId}`, {
      method: 'DELETE',
    }),
};

// Voiceovers API
export const voiceoversApi = {
  list: (projectId: string) =>
    fetchJson<VoiceoverFile[]>(`${API_BASE}/projects/${projectId}/voiceovers`),

  generate: (projectId: string, provider = 'edge', mock = false) =>
    fetchJson<JobResponse>(`${API_BASE}/projects/${projectId}/voiceovers/generate`, {
      method: 'POST',
      body: JSON.stringify({ provider, mock }),
    }),

  getAudioUrl: (projectId: string, sceneId: string) =>
    `${API_BASE}/projects/${projectId}/voiceovers/${sceneId}/audio`,
};

// Render API
export const renderApi = {
  list: (projectId: string) =>
    fetchJson<RenderInfo[]>(`${API_BASE}/projects/${projectId}/render`),

  start: (projectId: string, resolution = '1080p', preview = false) =>
    fetchJson<JobResponse>(`${API_BASE}/projects/${projectId}/render`, {
      method: 'POST',
      body: JSON.stringify({ resolution, preview }),
    }),

  getVideoUrl: (projectId: string, filename: string) =>
    `${API_BASE}/projects/${projectId}/render/video/${filename}`,
};

// Feedback API
export const feedbackApi = {
  list: (projectId: string) =>
    fetchJson<FeedbackItem[]>(`${API_BASE}/projects/${projectId}/feedback`),

  process: (projectId: string, feedbackText: string, dryRun = false) =>
    fetchJson<JobResponse>(`${API_BASE}/projects/${projectId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ feedback_text: feedbackText, dry_run: dryRun }),
    }),

  get: (projectId: string, feedbackId: string) =>
    fetchJson<FeedbackItem>(`${API_BASE}/projects/${projectId}/feedback/${feedbackId}`),
};

// Sound API
export const soundApi = {
  list: (projectId: string) =>
    fetchJson<SoundInfo[]>(`${API_BASE}/projects/${projectId}/sound`),

  generate: (projectId: string) =>
    fetchJson<JobResponse>(`${API_BASE}/projects/${projectId}/sound/generate`, {
      method: 'POST',
    }),

  getAudioUrl: (projectId: string, soundName: string) =>
    `${API_BASE}/projects/${projectId}/sound/${soundName}/audio`,
};

// Storyboard API
export const storyboardApi = {
  get: (projectId: string) =>
    fetchJson<Storyboard>(`${API_BASE}/projects/${projectId}/storyboard`),

  update: (projectId: string, storyboard: Storyboard) =>
    fetchJson<Storyboard>(`${API_BASE}/projects/${projectId}/storyboard`, {
      method: 'PUT',
      body: JSON.stringify(storyboard),
    }),
};

// Jobs API
export const jobsApi = {
  list: (projectId?: string) => {
    const url = projectId
      ? `${API_BASE}/jobs?project_id=${projectId}`
      : `${API_BASE}/jobs`;
    return fetchJson<Job[]>(url);
  },

  get: (jobId: string) => fetchJson<Job>(`${API_BASE}/jobs/${jobId}`),

  cancel: (jobId: string) =>
    fetchJson<void>(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' }),
};
