import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsService } from '../services/jobs';
import type { Job } from '../services/jobs';
import { MapPin, Building, Eye, Briefcase, Bookmark, BookmarkCheck, UserCheck, AlertCircle, Search, Filter } from 'lucide-react';
import ApplyModal from '../components/ApplyModal';

// ─── Twin-button styles ──────────────────────────────────────────────────────
const btnL = "flex-1 py-2.5 px-4 text-sm font-semibold rounded-xl border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all duration-200 cursor-pointer";

const WORK_MODE_LABELS: Record<string, { label: string; color: string }> = {
  onsite: { label: 'On-site', color: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30' },
  remote: { label: 'Remote',  color: 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-blue-900/30' },
  hybrid: { label: 'Hybrid',  color: 'text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-blue-900/30' },
};

const Jobs = () => {
  const navigate = useNavigate();
  const isLoggedIn = !!localStorage.getItem('access_token');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Apply logic state
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [eligibilityMsg, setEligibilityMsg] = useState<{ text: string; missing: string[] } | null>(null);

  // Filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [workModeFilter, setWorkModeFilter] = useState('all');
  const [minSalaryFilter, setMinSalaryFilter] = useState('');

  useEffect(() => {
    jobsService.getJobs()
      .then(data => setJobs(data || []))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load jobs.'))
      .finally(() => setIsLoading(false));
  }, []);

  const handleToggleSave = async (e: React.MouseEvent, job: Job) => {
    e.stopPropagation();
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    const wasSaved = !!job.is_saved;
    setJobs(prev => prev.map(j => j.id === job.id ? { ...j, is_saved: !wasSaved } : j));
    try {
      if (wasSaved) await jobsService.unsaveJob(job.id);
      else await jobsService.saveJob(job.id);
    } catch {
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, is_saved: wasSaved } : j));
    }
  };

  const handleApplyClick = async (e: React.MouseEvent, job: Job) => {
    e.stopPropagation();
    if (job.is_own_job || job.is_applied) return;
    
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    setEligibilityMsg(null);
    try {
      const eligibility = await jobsService.getApplyEligibility(job.id);
      if (!eligibility.eligible) {
        setEligibilityMsg({
          text: `Please update your profile to include: ${eligibility.missing_fields.join(', ')}.`,
          missing: eligibility.missing_fields
        });
        return;
      }
      setSelectedJob(job);
      setShowApplyModal(true);
    } catch (err: any) {
      console.error("Eligibility check failed", err);
    }
  };

  const confirmApply = async (message: string) => {
    if (!selectedJob) return;
    setIsApplying(true);
    try {
      await jobsService.applyForJob(selectedJob.id, true, message);
      setJobs(prev => prev.map(j => j.id === selectedJob.id ? { ...j, is_applied: true } : j));
      setShowApplyModal(false);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to apply.");
    } finally {
      setIsApplying(false);
    }
  };

  const jobTitle = (job: Job) => job.position || job.work || '(Untitled)';

  const activeFilterCount = (statusFilter !== 'all' ? 1 : 0) + (categoryFilter !== 'all' ? 1 : 0) + (workModeFilter !== 'all' ? 1 : 0) + (minSalaryFilter ? 1 : 0);

  const filteredJobs = jobs.filter(job => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const posMatch = job.position?.toLowerCase().includes(q) || job.work?.toLowerCase().includes(q) || jobTitle(job).toLowerCase().includes(q);
      const skillMatch = job.required_experience_fields?.toLowerCase().includes(q);
      const companyMatch = job.company?.toLowerCase().includes(q);
      if (!posMatch && !skillMatch && !companyMatch) return false;
    }
    
    if (statusFilter === 'applied' && !job.is_applied) return false;
    if (statusFilter === 'not_applied' && job.is_applied) return false;
    if (statusFilter === 'saved' && !job.is_saved) return false;

    if (categoryFilter !== 'all' && job.job_type !== categoryFilter) return false;
    if (workModeFilter !== 'all' && job.work_mode !== workModeFilter) return false;

    if (minSalaryFilter) {
      const minSal = parseInt(minSalaryFilter, 10);
      if (!isNaN(minSal)) {
        if (job.salary_min == null && job.salary_max == null) return false;
        if (job.salary_max != null && job.salary_max < minSal) return false;
      }
    }

    return true;
  });

  return (
    <>
      <div className="flex-1 flex flex-col p-4 sm:p-6 max-w-7xl mx-auto w-full">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Available Jobs</h1>
          <p className="text-zinc-500 dark:text-zinc-400">Find your next opportunity from our curated list of positions</p>
        </div>

        {/* Filters Section */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={18} />
            <input 
              type="text"
              placeholder="Search positions or skills..."
              className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100 dark:text-white"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors dark:text-zinc-50 shrink-0"
          >
            <Filter size={18} />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-full text-xs">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8 p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Interaction</label>
              <select 
                value={statusFilter} 
                onChange={e => setStatusFilter(e.target.value)}
                className="w-full p-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none dark:text-white"
              >
                <option value="all">All Jobs</option>
                <option value="applied">Applied</option>
                <option value="not_applied">Not Applied</option>
                <option value="saved">Saved</option>
              </select>
            </div>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Category</label>
              <select 
                value={categoryFilter} 
                onChange={e => setCategoryFilter(e.target.value)}
                className="w-full p-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none dark:text-white"
              >
                <option value="all">All Categories</option>
                <option value="corporate">Corporate</option>
                <option value="domestic">Domestic</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Work Mode</label>
              <select 
                value={workModeFilter} 
                onChange={e => setWorkModeFilter(e.target.value)}
                className="w-full p-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none dark:text-white"
              >
                <option value="all">All Modes</option>
                <option value="onsite">On-site</option>
                <option value="remote">Remote (WFH)</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Min. Salary (Yearly)</label>
              <input 
                type="number"
                placeholder="e.g. 50000"
                value={minSalaryFilter}
                onChange={e => setMinSalaryFilter(e.target.value)}
                className="w-full p-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none dark:text-white"
              />
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-400">Loading jobs…</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-red-500">{error}</div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-400">No jobs match your filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredJobs.map(job => {
              const wm = job.work_mode ? WORK_MODE_LABELS[job.work_mode] : null;
              const isOwn = !!job.is_own_job;

              return (
                <div
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col"
                >
                  {/* ── Header ── */}
                  <div className="flex justify-between items-start mb-3 gap-3">
                    <div className="flex-1 min-w-0">
                      <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 truncate">{jobTitle(job)}</h2>
                      <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                        {job.company && <span className="flex items-center gap-1.5"><Building size={13} />{job.company}</span>}
                        <span className="flex items-center gap-1.5"><MapPin size={13} />{job.location}</span>
                      </div>
                    </div>

                    <div className="relative group shrink-0" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={e => { if (!isOwn) handleToggleSave(e, job); }}
                        disabled={isOwn}
                        className={`p-2 rounded-xl transition-colors ${
                          isOwn
                            ? 'text-zinc-300 dark:text-zinc-600 bg-zinc-100 dark:bg-zinc-800 cursor-not-allowed'
                            : job.is_saved
                            ? 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30 hover:bg-blue-100'
                            : 'text-zinc-400 hover:text-zinc-700 bg-zinc-100 dark:bg-zinc-800 dark:hover:text-zinc-200'
                        }`}
                      >
                        {job.is_saved && !isOwn ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
                      </button>
                      {isOwn && (
                        <div className="absolute right-0 bottom-full mb-2 px-3 py-1.5 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 text-xs font-medium rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-lg z-10">
                          Cannot save your own job
                          <div className="absolute top-full right-3 border-4 border-transparent border-t-zinc-900 dark:border-t-zinc-100" />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ── Badges ── */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {job.job_type && (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300 capitalize">{job.job_type}</span>
                    )}
                    {job.type && (
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                        {job.type === 'full_time' ? 'Full Time' : 'Part Time'}
                      </span>
                    )}
                    {wm && (
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${wm.color}`}>{wm.label}</span>
                    )}
                    {isOwn && (
                      <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        <UserCheck size={11} /> Your Posting
                      </span>
                    )}
                  </div>

                  {/* ── Stats ── */}
                  <div className="flex items-center gap-4 text-xs text-zinc-400 mb-5">
                    <span className="flex items-center gap-1"><Eye size={12} />{job.viewed_count ?? 0} views</span>
                    <span className="flex items-center gap-1"><Briefcase size={12} />{job.applied_count ?? 0} applied</span>
                    <span className="flex items-center gap-1"><Bookmark size={12} />{job.saved_count ?? 0} saved</span>
                  </div>

                  {/* ── Actions ── */}
                  <div className="mt-auto pt-4 border-t border-zinc-100 dark:border-zinc-800 space-y-3">
                    {eligibilityMsg && eligibilityMsg.text && (
                       <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-xl">
                          <AlertCircle size={14} className="text-red-500 mt-0.5 shrink-0" />
                          <div className="flex-1">
                             <p className="text-xs text-red-700 dark:text-red-400 font-medium">
                                {eligibilityMsg.text}
                             </p>
                             <button 
                                onClick={(e) => { e.stopPropagation(); navigate('/profile'); }}
                                className="text-[10px] text-red-600 dark:text-red-400 font-bold underline mt-1 block"
                             >
                                Go to Profile Settings
                             </button>
                          </div>
                       </div>
                    )}

                    <div className="flex gap-3" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={e => { e.stopPropagation(); navigate(`/jobs/${job.id}`); }}
                        className={btnL}
                      >
                        View Details
                      </button>

                      <div className="flex-1 relative group">
                        <button
                          onClick={e => handleApplyClick(e, job)}
                          disabled={!!job.is_applied || isOwn}
                          className={`w-full py-2.5 px-4 text-sm font-semibold rounded-xl border-2 transition-all duration-200 ${
                            isOwn
                              ? 'border-zinc-300 dark:border-zinc-700 bg-zinc-300 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-400 cursor-not-allowed'
                              : job.is_applied
                              ? 'border-green-500 dark:border-green-600 bg-green-500 dark:bg-green-600 text-white cursor-default'
                              : 'border-zinc-900 dark:border-zinc-50 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:bg-transparent dark:hover:text-zinc-50'
                          }`}
                        >
                          {job.is_applied ? 'Applied ✓' : 'Apply Now'}
                        </button>
                        {isOwn && (
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 text-xs font-medium rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-lg z-10">
                            Cannot apply for your own job
                            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-zinc-900 dark:border-t-zinc-100" />
                          </div>
                        )}
                      </div>
                    </div>

                    {job.posted_by_username && (
                      <p className="text-xs text-zinc-400 text-right">
                        Posted by <span className="font-semibold text-zinc-500 dark:text-zinc-400">{job.posted_by_username}</span>
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Apply Confirmation Modal */}
      <ApplyModal 
        isOpen={showApplyModal}
        onClose={() => setShowApplyModal(false)}
        onConfirm={confirmApply}
        isSubmitting={isApplying}
        jobTitle={selectedJob ? jobTitle(selectedJob) : ''}
      />
    </>
  );
};

export default Jobs;
