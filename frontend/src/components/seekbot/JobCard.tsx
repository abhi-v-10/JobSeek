import React from 'react';
import { MapPin, Building2, Briefcase, ArrowRight, Wifi } from 'lucide-react';
import type { JobSearchResult } from '../../services/chatService';

interface JobCardProps {
  job: JobSearchResult;
  onViewDetails: (job: JobSearchResult) => void;
}

const JobCard: React.FC<JobCardProps> = ({ job, onViewDetails }) => {
  const skills = job.skills?.split(',').map(s => s.trim()).filter(Boolean).slice(0, 3) ?? [];

  const capitalize = (str: string) =>
    str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();

  const postedDate = new Date(job.created_at).toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
  });

  return (
    <button
      onClick={() => onViewDetails(job)}
      className="w-full text-left bg-zinc-900 hover:bg-zinc-800/80 border border-zinc-800 hover:border-zinc-700/80 rounded-xl p-4 transition-all group cursor-pointer"
    >
      {/* Top row: title + remote badge */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-sm font-semibold text-zinc-100 leading-tight line-clamp-1">
          {job.title}
        </span>
        {job.is_remote && (
          <span className="shrink-0 text-[11px] px-2 py-0.5 bg-emerald-900/40 text-emerald-400 border border-emerald-800/50 rounded-full flex items-center gap-1">
            <Wifi size={9} />
            Remote
          </span>
        )}
      </div>

      {/* Company row */}
      <div className="flex items-center gap-1.5 text-xs text-zinc-400 mb-2">
        <Building2 size={12} className="shrink-0 text-zinc-600" />
        <span>{job.company_name}</span>
      </div>

      {/* Location + type row */}
      <div className="flex items-center gap-3 text-xs text-zinc-500 mb-3">
        <span className="flex items-center gap-1">
          <MapPin size={11} className="shrink-0" />
          {job.location}
        </span>
        <span className="flex items-center gap-1">
          <Briefcase size={11} className="shrink-0" />
          {capitalize(job.job_type)}
        </span>
      </div>

      {/* Skills row */}
      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {skills.map((skill, i) => (
            <span
              key={i}
              className="text-[11px] px-2 py-0.5 bg-indigo-950/60 text-indigo-400 border border-indigo-800/40 rounded-md font-mono"
            >
              {skill}
            </span>
          ))}
        </div>
      )}

      {/* Footer row */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-zinc-600">{postedDate}</span>
        <span className="text-[11px] text-indigo-400 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          Details
          <ArrowRight size={10} />
        </span>
      </div>
    </button>
  );
};

export default JobCard;
