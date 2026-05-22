import React, { useState } from "react";
import { Bot, BriefcaseIcon } from "lucide-react";
import JobCard from "./JobCard";
import JobDetailModal from "./JobDetailModal";
import type { JobSearchResult } from "../../services/chatService";

interface JobResultsMessageProps {
  content: string;
  jobs?: JobSearchResult[];
}

const JobResultsMessage: React.FC<JobResultsMessageProps> = ({
  content,
  jobs,
}) => {
  const [selectedJob, setSelectedJob] = useState<JobSearchResult | null>(null);

  // ── Fallback: no structured data → plain text (no bubble) ───────────────────
  if (!jobs || jobs.length === 0) {
    return (
      <div className="flex items-start gap-4 mb-8 group">
        <div className="shrink-0 w-8 h-8 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 flex items-center justify-center group-hover:border-zinc-400 dark:group-hover:border-zinc-700 transition-colors shadow-sm mt-1">
          <Bot size={18} />
        </div>
        <div className="max-w-[85%]">
          <p className="text-[15px] text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap wrap-break-word">
            {content}
          </p>
        </div>
      </div>
    );
  }

  // ── Rich cards layout (No bubble) ────────────────────────────────────────────
  return (
    <>
      <div className="flex items-start gap-4 mb-10 group">
        {/* Bot avatar */}
        <div className="shrink-0 w-8 h-8 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 flex items-center justify-center group-hover:border-zinc-400 dark:group-hover:border-zinc-700 transition-colors shadow-sm mt-1">
          <Bot size={18} />
        </div>

        {/* Panel */}
        <div className="flex-1 min-w-0">
          {/* Summary / recommendation text (shown when content is provided) */}
          {content && (
            <div className="mb-5 space-y-1">
              {content.split("\n").map((line, i) =>
                line.trim() === "" ? (
                  <div key={i} className="h-2" />
                ) : (
                  <p
                    key={i}
                    className="text-[14px] text-zinc-700 dark:text-zinc-300 leading-relaxed"
                  >
                    {line}
                  </p>
                ),
              )}
            </div>
          )}

          {/* Header row */}
          <div className="flex items-center gap-2 mb-4">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
              <BriefcaseIcon size={14} className="text-indigo-400 shrink-0" />
            </div>
            <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Found{" "}
              <span className="font-bold text-indigo-400">{jobs.length}</span>{" "}
              matching job{jobs.length !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Card grid: 1 col default, 2 col on larger chat widths */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onViewDetails={setSelectedJob} />
            ))}
          </div>

          {/* Hint text */}
          <p className="text-[11px] text-zinc-500 mt-3 font-medium uppercase tracking-wider opacity-60">
            Click a card to see full details
          </p>
        </div>
      </div>

      {/* Detail modal — portal-free, fixed overlay */}
      {selectedJob && (
        <JobDetailModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </>
  );
};

export default JobResultsMessage;
