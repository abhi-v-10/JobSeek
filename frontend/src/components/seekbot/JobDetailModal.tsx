import React, { useState, useEffect } from "react";
import {
  X,
  MapPin,
  Building2,
  Briefcase,
  DollarSign,
  ExternalLink,
  Calendar,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { chatService } from "../../services/chatService";
import type { JobSearchResult, FullJobData } from "../../services/chatService";

interface JobDetailModalProps {
  job: JobSearchResult;
  onClose: () => void;
}

const WORK_MODE: Record<string, { label: string; cls: string }> = {
  onsite: {
    label: "On-site",
    cls: "text-blue-400 bg-blue-950/50 border-blue-800/50",
  },
  remote: {
    label: "Remote",
    cls: "text-emerald-400 bg-emerald-950/50 border-emerald-800/50",
  },
  hybrid: {
    label: "Hybrid",
    cls: "text-violet-400 bg-violet-950/50 border-violet-800/50",
  },
};

interface InfoTileProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const InfoTile: React.FC<InfoTileProps> = ({ icon, label, value }) => (
  <div className="bg-zinc-800/60 rounded-xl px-3 py-2.5 flex items-start gap-2">
    <span className="mt-0.5 shrink-0 text-zinc-500">{icon}</span>
    <div className="min-w-0">
      <p className="text-[10px] text-zinc-500 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-zinc-200 truncate">{value}</p>
    </div>
  </div>
);

const JobDetailModal: React.FC<JobDetailModalProps> = ({ job, onClose }) => {
  const navigate = useNavigate();
  const [fullJob, setFullJob] = useState<FullJobData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetch full job details
  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setFetchError(null);
    setFullJob(null);

    chatService
      .getJobDetail(job.id)
      .then((data) => {
        if (isMounted) {
          setFullJob(data);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setFetchError("Failed to load job details. Please try again.");
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [job.id]);

  // Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Derived display values
  const displayTitle = fullJob?.position || fullJob?.work || job.title;
  const displayCompany = fullJob?.company || job.company_name;
  const workModeKey =
    fullJob?.work_mode || (job.is_remote ? "remote" : "onsite");
  const workModeCfg = WORK_MODE[workModeKey] ?? WORK_MODE["onsite"];

  const skills = (fullJob?.required_experience_fields || job.skills || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const salaryMin = fullJob?.salary_min ?? null;
  const salaryMax = fullJob?.salary_max ?? null;
  let salary: string | null = null;
  if (salaryMin !== null && salaryMax !== null) {
    salary = `₹${salaryMin.toLocaleString()} – ₹${salaryMax.toLocaleString()}`;
  } else if (salaryMin !== null) {
    salary = `From ₹${salaryMin.toLocaleString()}`;
  } else if (salaryMax !== null) {
    salary = `Up to ₹${salaryMax.toLocaleString()}`;
  }

  const empType = fullJob?.type
    ? fullJob.type.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : null;

  const postedDate = new Date(job.created_at).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const handleOpenFullPage = () => {
    navigate("/jobs/" + job.id);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-200 flex items-end sm:items-center justify-center p-0 sm:p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div className="relative w-full sm:max-w-xl max-h-[90vh] sm:max-h-[82vh] flex flex-col bg-zinc-900 sm:rounded-2xl border border-zinc-700/50 shadow-2xl overflow-hidden rounded-t-2xl">
        {/* Header */}
        <div className="shrink-0 flex items-start justify-between p-5 border-b border-zinc-800">
          <div className="flex-1 min-w-0 mr-3">
            {isLoading ? (
              <div className="space-y-2 animate-pulse">
                <div className="h-4 bg-zinc-800 rounded w-3/4" />
                <div className="h-3 bg-zinc-800 rounded w-1/2" />
              </div>
            ) : (
              <>
                <h2 className="text-base font-semibold text-zinc-100 leading-snug line-clamp-2">
                  {displayTitle}
                </h2>
                <div className="flex items-center gap-1.5 mt-1 text-sm text-zinc-400">
                  <Building2 size={13} className="shrink-0 text-zinc-600" />
                  <span className="truncate">{displayCompany}</span>
                </div>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors shrink-0"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-14 bg-zinc-800 rounded-xl animate-pulse"
                />
              ))}
            </div>
          ) : fetchError ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-zinc-500 text-sm">{fetchError}</p>
            </div>
          ) : fullJob ? (
            <>
              {/* Badges row */}
              <div className="flex flex-wrap gap-2">
                <span
                  className={`text-xs px-3 py-1 rounded-full border font-medium ${workModeCfg.cls}`}
                >
                  {workModeCfg.label}
                </span>
                {empType && (
                  <span className="text-xs px-3 py-1 rounded-full border border-zinc-700 text-zinc-300 bg-zinc-800">
                    {empType}
                  </span>
                )}
                {fullJob.required_experience_years != null && (
                  <span className="text-xs px-3 py-1 rounded-full border border-zinc-700 text-zinc-400 bg-zinc-800">
                    {fullJob.required_experience_years}+ yrs exp
                  </span>
                )}
              </div>

              {/* Info grid */}
              <div className="grid grid-cols-2 gap-2">
                <InfoTile
                  icon={<MapPin size={13} />}
                  label="Location"
                  value={fullJob.location || job.location}
                />
                {salary && (
                  <InfoTile
                    icon={<DollarSign size={13} />}
                    label="Salary"
                    value={salary}
                  />
                )}
                <InfoTile
                  icon={<Briefcase size={13} />}
                  label="Job Type"
                  value={fullJob.job_type}
                />
                <InfoTile
                  icon={<Calendar size={13} />}
                  label="Posted"
                  value={postedDate}
                />
              </div>

              {/* Skills section */}
              {skills.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    Required Skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {skills.map((skill, i) => (
                      <span
                        key={i}
                        className="text-xs px-2.5 py-1 bg-indigo-950/50 text-indigo-300 border border-indigo-800/40 rounded-lg font-mono"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description section */}
              {fullJob.description && (
                <div>
                  <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    Description
                  </p>
                  <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                    {fullJob.description}
                  </p>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="shrink-0 flex gap-3 p-4 border-t border-zinc-800">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-medium text-zinc-400 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleOpenFullPage}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition-colors"
          >
            <ExternalLink size={14} />
            Open Full Page
          </button>
        </div>
      </div>
    </div>
  );
};

export default JobDetailModal;
