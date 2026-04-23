// Job Details Page
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import { jobsService } from '../services/jobs';
import type { Job } from '../services/jobs';
import { MapPin, Building, Eye, Briefcase, Bookmark, BookmarkCheck, Monitor, Home, Layers, UserCheck, Clock, DollarSign, AlertCircle } from 'lucide-react';
import ApplyModal from '../components/ApplyModal';

const WORK_MODE_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  onsite:  { label: 'On-site',  icon: <Monitor size={14} />,  color: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30' },
  remote:  { label: 'Remote',   icon: <Home size={14} />,     color: 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/30' },
  hybrid:  { label: 'Hybrid',   icon: <Layers size={14} />,   color: 'text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-green-900/30' },
};

const JobDetails = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isApplying, setIsApplying] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  
  // Apply logic
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [eligibilityMsg, setEligibilityMsg] = useState<{ text: string; missing: string[] } | null>(null);

  useEffect(() => {
    const fetchAndView = async () => {
      if (!id) return;
      try {
        // Record view silently, then fetch full details
        jobsService.viewJob(id).catch(() => {});
        const details = await jobsService.getJobDetails(id);
        setJob(details);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load job details.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchAndView();
  }, [id]);

  const handleApplyClick = async () => {
    if (!job || !id || job.is_own_job || job.is_applied) return;
    
    setEligibilityMsg(null);
    try {
      const eligibility = await jobsService.getApplyEligibility(id);
      if (!eligibility.eligible) {
        setEligibilityMsg({
          text: `Please update your profile to include: ${eligibility.missing_fields.join(', ')}.`,
          missing: eligibility.missing_fields
        });
        return;
      }
      setShowApplyModal(true);
    } catch (err: any) {
      console.error("Eligibility check failed", err);
    }
  };

  const confirmApply = async (message: string) => {
    if (!job || !id) return;
    setIsApplying(true);
    try {
      await jobsService.applyForJob(id, true, message);
      setJob(prev => prev ? { ...prev, is_applied: true } : null);
      setShowApplyModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to apply.");
    } finally {
      setIsApplying(false);
    }
  };

  const handleToggleSave = async () => {
    if (!job || !id) return;
    const wasSaved = !!job.is_saved;
    setJob(prev => prev ? { ...prev, is_saved: !wasSaved } : null);
    setIsSaving(true);
    try {
      if (wasSaved) await jobsService.unsaveJob(id);
      else await jobsService.saveJob(id);
    } catch {
      setJob(prev => prev ? { ...prev, is_saved: wasSaved } : null);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-zinc-400">Loading job details…</p>
        </div>
      </ProtectedRoute>
    );
  }

  if (error || !job) {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <p className="text-red-500">{error || 'Job not found'}</p>
          <button
            onClick={() => navigate('/jobs')}
            className="py-2.5 px-6 text-sm font-semibold rounded-lg border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all cursor-pointer"
          >
            Back to Jobs
          </button>
        </div>
      </ProtectedRoute>
    );
  }

  const isOwn = !!job.is_own_job;
  const wm = job.work_mode ? WORK_MODE_LABELS[job.work_mode] : null;
  const jobTitle = job.position || job.work || '(Untitled)';

  return (
    <ProtectedRoute>
      <div className="flex-1 flex flex-col p-6 max-w-4xl mx-auto w-full">
        <button
          onClick={() => navigate('/jobs')}
          className="self-start text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50 mb-6 transition-colors cursor-pointer"
        >
          ← Back to jobs
        </button>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm">

          {/* ── Top header ── */}
          <div className="flex justify-between items-start mb-4 gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">{jobTitle}</h1>
              <div className="flex flex-wrap items-center gap-4 text-zinc-500 dark:text-zinc-400 text-sm">
                {job.company && (
                  <span className="flex items-center gap-1.5"><Building size={15} />{job.company}</span>
                )}
                <span className="flex items-center gap-1.5"><MapPin size={15} />{job.location}</span>
                {job.posted_by_username && (
                  <span className="text-zinc-400 dark:text-zinc-500">
                    Posted by <span className="font-medium">{job.posted_by_username}</span>
                  </span>
                )}
              </div>
            </div>

            {!isOwn && (
              <button
                onClick={handleToggleSave}
                disabled={isSaving}
                className={`p-2.5 rounded-xl transition-colors shrink-0 cursor-pointer ${
                  job.is_saved
                    ? 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30'
                    : 'text-zinc-400 hover:text-zinc-700 bg-zinc-100 dark:bg-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                {job.is_saved ? <BookmarkCheck size={22} /> : <Bookmark size={22} />}
              </button>
            )}
          </div>

          {/* ── Badges ── */}
          <div className="flex flex-wrap gap-2 mb-6">
            {job.job_type && (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 capitalize">
                {job.job_type}
              </span>
            )}
            {job.type && (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                {job.type === 'full_time' ? 'Full Time' : 'Part Time'}
              </span>
            )}
            {wm && (
              <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${wm.color}`}>
                {wm.icon}{wm.label}
              </span>
            )}
            {isOwn && (
              <span className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <UserCheck size={12} /> Your Posting
              </span>
            )}
          </div>

          {/* ── Stats row ── */}
          <div className="flex flex-wrap gap-3 mb-8">
            {[
              { icon: <Eye size={15} />, label: `${job.viewed_count ?? 0} views` },
              { icon: <Briefcase size={15} />, label: `${job.applied_count ?? 0} applied` },
              { icon: <Bookmark size={15} />, label: `${job.saved_count ?? 0} saved` },
            ].map(stat => (
              <div key={stat.label} className="flex items-center gap-2 px-4 py-2 bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800 rounded-xl text-sm text-zinc-500 dark:text-zinc-400">
                {stat.icon} {stat.label}
              </div>
            ))}
          </div>

          {/* ── Salary / experience details ── */}
          {(job.salary_min || job.salary_max || job.required_experience_years || job.hourly_wage) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8 p-4 bg-zinc-50 dark:bg-zinc-800/40 rounded-xl border border-zinc-100 dark:border-zinc-800">
              {(job.salary_min || job.salary_max) && (
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 dark:text-green-400 shrink-0">
                    <DollarSign size={16} />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Salary</p>
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                      ₹{job.salary_min?.toLocaleString()} – ₹{job.salary_max?.toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
              {job.required_experience_years != null && (
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                    <Clock size={16} />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Experience Required</p>
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                      {job.required_experience_years}+ years
                    </p>
                  </div>
                </div>
              )}
              {job.hourly_wage && (
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0">
                    <DollarSign size={16} />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Hourly Wage</p>
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{job.hourly_wage}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Required skills ── */}
          {job.required_experience_fields && (
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 mb-2 uppercase tracking-wide">Required Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.required_experience_fields.split(',').map(s => s.trim()).filter(Boolean).map(skill => (
                  <span key={skill} className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── Description ── */}
          <div className="mb-8">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 mb-3">Job Description</h3>
            <div className="text-zinc-600 dark:text-zinc-300 text-sm leading-relaxed whitespace-pre-line">
              {job.description || 'No description provided.'}
            </div>
          </div>

          {/* ── Action buttons ── */}
          <div className="pt-6 border-t border-zinc-200 dark:border-zinc-800 space-y-4">
            {eligibilityMsg && (
              <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-2xl">
                <AlertCircle size={18} className="text-red-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm text-red-700 dark:text-red-400 font-medium leading-relaxed">
                    {eligibilityMsg.text}
                  </p>
                  <button 
                    onClick={() => navigate('/profile')}
                    className="text-xs text-red-600 dark:text-red-400 font-bold underline mt-2 block"
                  >
                    Go to Profile Settings
                  </button>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              {isOwn ? (
                <>
                  <button
                    onClick={() => navigate('/my-jobs')}
                    className="flex-1 py-3 px-6 text-sm font-semibold rounded-2xl border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all duration-200 cursor-pointer"
                  >
                    Manage This Job
                  </button>
                  <div className="flex-1 relative group">
                    <button
                      disabled
                      className="w-full py-3 px-6 text-sm font-semibold rounded-2xl border-2 border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500 cursor-not-allowed"
                    >
                      Apply Now
                    </button>
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 text-xs font-medium rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-lg">
                      You cannot apply for your own job posting
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-zinc-900 dark:border-t-zinc-100" />
                    </div>
                  </div>
                </>
              ) : (
                <button
                  onClick={handleApplyClick}
                  disabled={!!job.is_applied || isApplying}
                  className={`flex-1 py-3 px-8 text-sm font-semibold rounded-2xl border-2 transition-all duration-200 cursor-pointer ${
                    job.is_applied
                      ? 'border-green-500 dark:border-green-600 bg-green-500 dark:bg-green-600 text-white cursor-default'
                      : 'border-zinc-900 dark:border-zinc-50 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:bg-transparent dark:hover:text-zinc-50 active:scale-[0.98]'
                  }`}
                >
                  {isApplying ? 'Applying…' : job.is_applied ? 'Applied ✓' : 'Apply Now'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <ApplyModal 
        isOpen={showApplyModal}
        onClose={() => setShowApplyModal(false)}
        onConfirm={confirmApply}
        isSubmitting={isApplying}
        jobTitle={jobTitle}
      />
    </ProtectedRoute>
  );
};

export default JobDetails;
