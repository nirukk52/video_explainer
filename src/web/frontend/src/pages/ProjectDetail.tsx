import { useState, useEffect, useCallback } from 'react';
import { projectsApi, narrationsApi, voiceoversApi, renderApi, feedbackApi, storyboardApi } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import type { ProjectDetail as ProjectDetailType, Narration, Job, Storyboard } from '../types';

interface ProjectDetailProps {
  projectId: string;
  onBack: () => void;
}

type TabId = 'overview' | 'narrations' | 'voiceovers' | 'storyboard' | 'render' | 'feedback';

export function ProjectDetail({ projectId, onBack }: ProjectDetailProps) {
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);

  const handleJobUpdate = useCallback((job: Job) => {
    setJobs((prev) => {
      const index = prev.findIndex((j) => j.job_id === job.job_id);
      if (index >= 0) {
        const updated = [...prev];
        updated[index] = job;
        return updated;
      }
      return [job, ...prev];
    });
  }, []);

  useWebSocket({ projectId, onJobUpdate: handleJobUpdate });

  useEffect(() => {
    loadProject();
  }, [projectId]);

  async function loadProject() {
    try {
      setLoading(true);
      const data = await projectsApi.get(projectId);
      setProject(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading project...</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
        <p className="text-red-400">{error || 'Project not found'}</p>
        <button onClick={onBack} className="mt-2 text-sm text-red-300 hover:text-red-200">
          Back to projects
        </button>
      </div>
    );
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'narrations', label: 'Narrations' },
    { id: 'voiceovers', label: 'Voiceovers' },
    { id: 'storyboard', label: 'Storyboard' },
    { id: 'render', label: 'Render' },
    { id: 'feedback', label: 'Feedback' },
  ];

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-white">{project.title}</h1>
      </div>

      {/* Active Jobs Banner */}
      {jobs.filter((j) => j.status === 'running' || j.status === 'pending').length > 0 && (
        <div className="mb-6 bg-primary-500/10 border border-primary-500/50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-primary-400 mb-2">Active Jobs</h3>
          {jobs
            .filter((j) => j.status === 'running' || j.status === 'pending')
            .map((job) => (
              <div key={job.job_id} className="flex items-center gap-4">
                <span className="text-sm text-gray-300">{job.type}</span>
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all"
                    style={{ width: `${job.progress * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400">{job.message}</span>
              </div>
            ))}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-700 mb-6">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-4 px-1 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-primary-400 border-b-2 border-primary-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab project={project} />}
      {activeTab === 'narrations' && <NarrationsTab projectId={projectId} />}
      {activeTab === 'voiceovers' && <VoiceoversTab projectId={projectId} onJobStarted={handleJobUpdate} />}
      {activeTab === 'storyboard' && <StoryboardTab projectId={projectId} />}
      {activeTab === 'render' && <RenderTab projectId={projectId} onJobStarted={handleJobUpdate} />}
      {activeTab === 'feedback' && <FeedbackTab projectId={projectId} onJobStarted={handleJobUpdate} />}
    </div>
  );
}

function OverviewTab({ project }: { project: ProjectDetailType }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Video Settings</h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-400">Resolution</dt>
            <dd className="text-white">{project.video.width}x{project.video.height}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">FPS</dt>
            <dd className="text-white">{project.video.fps}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Target Duration</dt>
            <dd className="text-white">{project.video.target_duration_seconds}s</dd>
          </div>
        </dl>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Files Status</h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-400">Narrations</dt>
            <dd className="text-white">{project.files.narrations_count} scenes</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Voiceovers</dt>
            <dd className="text-white">{project.files.voiceover_count} files</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Storyboard</dt>
            <dd className={project.files.has_storyboard ? 'text-green-400' : 'text-gray-500'}>
              {project.files.has_storyboard ? 'Ready' : 'Not generated'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Rendered Videos</dt>
            <dd className="text-white">{project.files.rendered_videos.length}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

function NarrationsTab({ projectId }: { projectId: string }) {
  const [narrations, setNarrations] = useState<Narration[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  useEffect(() => {
    loadNarrations();
  }, [projectId]);

  async function loadNarrations() {
    try {
      setLoading(true);
      const data = await narrationsApi.list(projectId);
      setNarrations(data);
    } catch (e) {
      console.error('Failed to load narrations:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(sceneId: string) {
    try {
      await narrationsApi.update(projectId, sceneId, { narration: editText });
      setEditing(null);
      loadNarrations();
    } catch (e) {
      console.error('Failed to update narration:', e);
    }
  }

  if (loading) {
    return <div className="text-gray-400">Loading narrations...</div>;
  }

  if (narrations.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">No narrations found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {narrations.map((narration) => (
        <div
          key={narration.scene_id}
          className="bg-gray-800 rounded-lg p-4 border border-gray-700"
        >
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium text-white">{narration.title}</h4>
            <span className="text-xs text-gray-400">
              {narration.scene_id} • {narration.duration_seconds}s
            </span>
          </div>
          {editing === narration.scene_id ? (
            <div>
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white resize-none focus:outline-none focus:border-primary-500"
                rows={4}
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => handleSave(narration.scene_id)}
                  className="px-3 py-1 bg-primary-600 text-white text-sm rounded"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditing(null)}
                  className="px-3 py-1 text-gray-400 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-gray-300 text-sm">{narration.narration}</p>
              <button
                onClick={() => {
                  setEditing(narration.scene_id);
                  setEditText(narration.narration);
                }}
                className="mt-2 text-xs text-primary-400 hover:text-primary-300"
              >
                Edit
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function VoiceoversTab({ projectId, onJobStarted }: { projectId: string; onJobStarted: (job: Job) => void }) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    try {
      setGenerating(true);
      setError(null);
      const response = await voiceoversApi.generate(projectId);
      onJobStarted({
        job_id: response.job_id,
        type: 'voiceover',
        project_id: projectId,
        status: 'pending',
        progress: 0,
        message: response.message,
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to start voiceover generation';
      setError(message);
      console.error('Failed to start voiceover generation:', e);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      )}
      <button
        onClick={handleGenerate}
        disabled={generating}
        className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 text-white rounded-lg"
      >
        {generating ? 'Starting...' : 'Generate Voiceovers'}
      </button>
    </div>
  );
}

function StoryboardTab({ projectId }: { projectId: string }) {
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStoryboard();
  }, [projectId]);

  async function loadStoryboard() {
    try {
      setLoading(true);
      const data = await storyboardApi.get(projectId);
      setStoryboard(data);
    } catch (e) {
      console.error('Failed to load storyboard:', e);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="text-gray-400">Loading storyboard...</div>;
  }

  if (!storyboard) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">No storyboard generated yet</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 text-sm text-gray-400">
        Total duration: {storyboard.total_duration_seconds}s
      </div>
      <div className="space-y-2">
        {storyboard.scenes.map((scene) => (
          <div
            key={scene.id}
            className="bg-gray-800 rounded-lg p-4 border border-gray-700"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-white">{scene.title}</span>
              <span className="text-xs text-gray-400">
                {scene.audio_duration_seconds}s
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RenderTab({ projectId, onJobStarted }: { projectId: string; onJobStarted: (job: Job) => void }) {
  const [rendering, setRendering] = useState(false);
  const [resolution, setResolution] = useState('1080p');
  const [error, setError] = useState<string | null>(null);

  async function handleRender() {
    try {
      setRendering(true);
      setError(null);
      const response = await renderApi.start(projectId, resolution);
      onJobStarted({
        job_id: response.job_id,
        type: 'render',
        project_id: projectId,
        status: 'pending',
        progress: 0,
        message: response.message,
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to start render';
      setError(message);
      console.error('Failed to start render:', e);
    } finally {
      setRendering(false);
    }
  }

  return (
    <div>
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      )}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={resolution}
          onChange={(e) => setResolution(e.target.value)}
          className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
        >
          <option value="720p">720p</option>
          <option value="1080p">1080p (Recommended)</option>
          <option value="1440p">1440p</option>
          <option value="4k">4K</option>
        </select>
        <button
          onClick={handleRender}
          disabled={rendering}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 text-white rounded-lg"
        >
          {rendering ? 'Starting...' : 'Start Render'}
        </button>
      </div>
    </div>
  );
}

function FeedbackTab({ projectId, onJobStarted }: { projectId: string; onJobStarted: (job: Job) => void }) {
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!feedback.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      const response = await feedbackApi.process(projectId, feedback);
      onJobStarted({
        job_id: response.job_id,
        type: 'feedback',
        project_id: projectId,
        status: 'pending',
        progress: 0,
        message: response.message,
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setFeedback('');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to submit feedback';
      setError(message);
      console.error('Failed to submit feedback:', e);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Enter your feedback... e.g., 'Make the introduction more engaging' or 'Add more examples in scene 2'"
          rows={4}
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 resize-none focus:outline-none focus:border-primary-500"
        />
        <button
          type="submit"
          disabled={submitting || !feedback.trim()}
          className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 text-white rounded-lg"
        >
          {submitting ? 'Processing...' : 'Submit Feedback'}
        </button>
      </form>
    </div>
  );
}
