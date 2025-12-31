import type { ProjectSummary } from '../types';

interface ProjectCardProps {
  project: ProjectSummary;
  onClick: () => void;
}

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-gray-800 rounded-lg p-6 cursor-pointer hover:bg-gray-750 transition-colors border border-gray-700 hover:border-primary-500"
    >
      <h3 className="text-lg font-semibold text-white mb-2">{project.title}</h3>
      {project.description && (
        <p className="text-gray-400 text-sm mb-4 line-clamp-2">
          {project.description}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <StatusBadge
          label="Narrations"
          active={project.has_narrations}
        />
        <StatusBadge
          label="Voiceovers"
          active={project.has_voiceovers}
        />
        <StatusBadge
          label="Storyboard"
          active={project.has_storyboard}
        />
        <StatusBadge
          label="Rendered"
          active={project.has_render}
        />
      </div>
    </div>
  );
}

interface StatusBadgeProps {
  label: string;
  active: boolean;
}

function StatusBadge({ label, active }: StatusBadgeProps) {
  return (
    <span
      className={`px-2 py-1 text-xs rounded-full ${
        active
          ? 'bg-green-500/20 text-green-400 border border-green-500/50'
          : 'bg-gray-700 text-gray-500 border border-gray-600'
      }`}
    >
      {label}
    </span>
  );
}
