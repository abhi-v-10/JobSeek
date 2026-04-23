import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import { jobsService } from '../services/jobs';
import type { MyJob, PostJobPayload } from '../services/jobs';
import {
  Briefcase, Eye, Bookmark, Users, MapPin, Building,
  ChevronDown, ChevronUp, Pencil, X, Check, ToggleLeft, ToggleRight,
} from 'lucide-react';

const WORK_MODE_OPTIONS = [
  { value: 'onsite', label: 'On-site' },
  { value: 'remote', label: 'Remote / WFH' },
  { value: 'hybrid', label: 'Hybrid' },
];
const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'part_time', label: 'Part Time' },
];
const APPLICATION_STATUS_BADGE: Record<string, string> = {
  applied:   'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  reviewing: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  accepted:  'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected:  'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const inputCls = "w-full px-3 py-2.5 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors";
const labelCls = "block text-xs font-semibold text-zinc-500 dark:text-zinc-400 mb-1.5 uppercase tracking-wide";

const MyJobs = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<MyJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedApplicants, setExpandedApplicants] = useState<Set<number | string>>(new Set());
  const [editingId, setEditingId] = useState<number | string | null>(null);
  const [editForm, setEditForm] = useState<Partial<PostJobPayload & { status: string }>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState<Set<number | string>>(new Set());

  useEffect(() => {
    jobsService.getMyJobs()
      .then(data => setJobs(data || []))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load your jobs.'))
      .finally(() => setIsLoading(false));
  }, []);

  const toggleApplicants = (id: number | string) => {
    setExpandedApplicants(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const startEdit = (job: MyJob) => {
    setEditingId(job.id);
    setEditForm({
      company: job.company,
      position: job.position,
      location: job.location,
      type: job.type,
      salary_min: job.salary_min,
      salary_max: job.salary_max,
      description: job.description,
      work_mode: job.work_mode,
      required_experience_years: job.required_experience_years,
      required_experience_fields: job.required_experience_fields,
      work: job.work,
      daily_work_time: job.daily_work_time,
      hourly_wage: job.hourly_wage,
    });
  };

  const cancelEdit = () => { setEditingId(null); setEditForm({}); };

  const saveEdit = async (jobId: number | string) => {
    setIsSaving(true);
    try {
      const updated = await jobsService.updateJob(jobId, editForm);
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, ...updated } : j));
      setEditingId(null);
      setEditForm({});
    } catch (err: any) {
      alert(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to save changes.');
    } finally {
      setIsSaving(false);
    }
  };

  const toggleStatus = async (job: MyJob) => {
    const newStatus = job.status === 'open' ? 'closed' : 'open';
    setTogglingStatus(prev => new Set(prev).add(job.id));
    try {
      const updated = await jobsService.updateJob(job.id, { status: newStatus } as any);
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: updated.status } : j));
    } catch (err: any) {
      alert('Failed to update job status.');
    } finally {
      setTogglingStatus(prev => {
        const next = new Set(prev);
        next.delete(job.id);
        return next;
      });
    }
  };

  const jobTitle = (job: MyJob) => job.position || job.work || '(Untitled)';

  return (
    <ProtectedRoute>
      <div className="flex-1 flex flex-col p-6 max-w-4xl mx-auto w-full">

        {/* ── Page header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">My Job Postings</h1>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">Manage and track all the jobs you've posted</p>
          </div>
          <button
            onClick={() => navigate('/post-job')}
            className="flex items-center justify-center gap-2 py-2.5 px-5 text-sm font-semibold rounded-xl bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-all shrink-0"
          >
            + Post New Job
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-400">Loading your jobs…</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-red-500">{error}</div>
        ) : jobs.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center py-24">
            <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4">
              <Briefcase size={28} className="text-zinc-400" />
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 font-medium mb-1">No jobs posted yet</p>
            <p className="text-zinc-400 text-sm mb-6">Start hiring by posting your first job</p>
            <button
              onClick={() => navigate('/post-job')}
              className="py-2.5 px-6 text-sm font-semibold rounded-xl bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-zinc-700 transition-all"
            >
              Post Your First Job
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {jobs.map(job => {
              const isEditing = editingId === job.id;
              const showApplicants = expandedApplicants.has(job.id);
              const isCorporate = job.job_type === 'corporate';
              const isOpen = job.status === 'open';
              const isTogglingThis = togglingStatus.has(job.id);

              return (
                <div key={job.id} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">

                  {/* ── Closed banner ── */}
                  {!isOpen && (
                    <div className="px-6 py-2 bg-zinc-100 dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-zinc-400 shrink-0" />
                      <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">This job is closed — no longer accepting applications</p>
                    </div>
                  )}

                  {/* ── Main content ── */}
                  <div className="p-6">
                    {/* Title row */}
                    <div className="flex items-start justify-between gap-4 mb-1">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2.5 mb-1">
                          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">{jobTitle(job)}</h2>
                          {/* Status badge */}
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            isOpen
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
                          }`}>
                            {isOpen ? 'Open' : 'Closed'}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400">
                          {job.company && <span className="flex items-center gap-1.5"><Building size={13} />{job.company}</span>}
                          <span className="flex items-center gap-1.5"><MapPin size={13} />{job.location}</span>
                          <span className="capitalize text-xs px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded-full">{job.job_type}</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 shrink-0">
                        {/* Status toggle */}
                        <button
                          onClick={() => toggleStatus(job)}
                          disabled={isTogglingThis}
                          title={isOpen ? 'Close this job' : 'Reopen this job'}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            isOpen
                              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/40'
                              : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                          } disabled:opacity-50`}
                        >
                          {isOpen ? <ToggleRight size={15} /> : <ToggleLeft size={15} />}
                          {isTogglingThis ? '…' : isOpen ? 'Close Job' : 'Reopen'}
                        </button>

                        {/* Edit / Save / Cancel */}
                        {isEditing ? (
                          <>
                            <button
                              onClick={cancelEdit}
                              title="Cancel"
                              className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors"
                            >
                              <X size={16} />
                            </button>
                            <button
                              onClick={() => saveEdit(job.id)}
                              disabled={isSaving}
                              title="Save changes"
                              className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
                            >
                              <Check size={16} />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => startEdit(job)}
                            title="Edit job"
                            className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors"
                          >
                            <Pencil size={16} />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="flex gap-5 mt-4 pb-4 border-b border-zinc-100 dark:border-zinc-800">
                      <div className="flex items-center gap-1.5 text-sm">
                        <Eye size={14} className="text-blue-500" />
                        <span className="font-bold text-zinc-900 dark:text-zinc-50">{job.viewed_count ?? 0}</span>
                        <span className="text-zinc-400 text-xs">views</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-sm">
                        <Briefcase size={14} className="text-green-500" />
                        <span className="font-bold text-zinc-900 dark:text-zinc-50">{job.applied_count ?? 0}</span>
                        <span className="text-zinc-400 text-xs">applied</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-sm">
                        <Bookmark size={14} className="text-purple-500" />
                        <span className="font-bold text-zinc-900 dark:text-zinc-50">{job.saved_count ?? 0}</span>
                        <span className="text-zinc-400 text-xs">saved</span>
                      </div>
                    </div>

                    {/* ── Inline edit form ── */}
                    {isEditing && (
                      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {isCorporate && (
                          <>
                            <div>
                              <label className={labelCls}>Company</label>
                              <input className={inputCls} value={editForm.company || ''} onChange={e => setEditForm(p => ({ ...p, company: e.target.value }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Position</label>
                              <input className={inputCls} value={editForm.position || ''} onChange={e => setEditForm(p => ({ ...p, position: e.target.value }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Employment Type</label>
                              <select className={inputCls} value={editForm.type || ''} onChange={e => setEditForm(p => ({ ...p, type: e.target.value }))}>
                                {EMPLOYMENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className={labelCls}>Experience (years)</label>
                              <input type="number" className={inputCls} value={editForm.required_experience_years ?? ''} onChange={e => setEditForm(p => ({ ...p, required_experience_years: e.target.value ? parseInt(e.target.value) : undefined }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Salary Min (₹)</label>
                              <input type="number" className={inputCls} value={editForm.salary_min ?? ''} onChange={e => setEditForm(p => ({ ...p, salary_min: e.target.value ? parseInt(e.target.value) : undefined }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Salary Max (₹)</label>
                              <input type="number" className={inputCls} value={editForm.salary_max ?? ''} onChange={e => setEditForm(p => ({ ...p, salary_max: e.target.value ? parseInt(e.target.value) : undefined }))} />
                            </div>
                            <div className="sm:col-span-2">
                              <label className={labelCls}>Required Skills / Tech Stack</label>
                              <input className={inputCls} placeholder="e.g. React, Django, PostgreSQL" value={editForm.required_experience_fields || ''} onChange={e => setEditForm(p => ({ ...p, required_experience_fields: e.target.value }))} />
                            </div>
                          </>
                        )}
                        {!isCorporate && (
                          <>
                            <div>
                              <label className={labelCls}>Work Type</label>
                              <input className={inputCls} value={editForm.work || ''} onChange={e => setEditForm(p => ({ ...p, work: e.target.value }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Daily Work Hours</label>
                              <input type="number" className={inputCls} value={editForm.daily_work_time ?? ''} onChange={e => setEditForm(p => ({ ...p, daily_work_time: e.target.value ? parseInt(e.target.value) : undefined }))} />
                            </div>
                            <div>
                              <label className={labelCls}>Hourly Wage</label>
                              <input className={inputCls} value={editForm.hourly_wage || ''} onChange={e => setEditForm(p => ({ ...p, hourly_wage: e.target.value }))} />
                            </div>
                          </>
                        )}
                        <div>
                          <label className={labelCls}>Location</label>
                          <input className={inputCls} value={editForm.location || ''} onChange={e => setEditForm(p => ({ ...p, location: e.target.value }))} />
                        </div>
                        <div>
                          <label className={labelCls}>Work Mode</label>
                          <select className={inputCls} value={editForm.work_mode || 'onsite'} onChange={e => setEditForm(p => ({ ...p, work_mode: e.target.value }))}>
                            {WORK_MODE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        </div>
                        <div className="sm:col-span-2">
                          <label className={labelCls}>Description</label>
                          <textarea rows={4} className={inputCls} placeholder="Describe the role, responsibilities, and requirements…" value={editForm.description || ''} onChange={e => setEditForm(p => ({ ...p, description: e.target.value }))} />
                        </div>

                        {/* Save / cancel inside form */}
                        <div className="sm:col-span-2 flex gap-3 pt-2">
                          <button onClick={cancelEdit} className="flex-1 py-2.5 px-5 text-sm font-semibold rounded-xl border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all duration-200 cursor-pointer">
                            Cancel
                          </button>
                          <button onClick={() => saveEdit(job.id)} disabled={isSaving} className="flex-1 py-2.5 px-5 text-sm font-semibold rounded-xl border-2 border-zinc-900 dark:border-zinc-50 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:bg-transparent dark:hover:text-zinc-50 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">
                            {isSaving ? 'Saving…' : 'Save Changes'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* ── Applicants section ── */}
                  <button
                    onClick={() => toggleApplicants(job.id)}
                    className="w-full flex items-center justify-between px-6 py-3.5 bg-zinc-50 dark:bg-zinc-800/60 border-t border-zinc-100 dark:border-zinc-800 text-sm font-semibold text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Users size={15} className="text-zinc-400" />
                      {job.applicants?.length ?? 0} Applicant{(job.applicants?.length ?? 0) !== 1 ? 's' : ''}
                    </span>
                    {showApplicants ? <ChevronUp size={15} className="text-zinc-400" /> : <ChevronDown size={15} className="text-zinc-400" />}
                  </button>

                  {showApplicants && (
                    <div className="border-t border-zinc-100 dark:border-zinc-800">
                      {!job.applicants || job.applicants.length === 0 ? (
                        <div className="px-6 py-6 text-center">
                          <p className="text-sm text-zinc-400">No applicants yet</p>
                        </div>
                      ) : (
                        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                          {job.applicants.map((app, idx) => (
                            <div key={app.id} className="flex items-center justify-between px-6 py-4 gap-4">
                              <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-sm font-bold text-zinc-500 dark:text-zinc-400 shrink-0">
                                  {(app.full_name || app.username).charAt(0).toUpperCase()}
                                </div>
                                <div>
                                  <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                                    {app.full_name || app.username}
                                  </p>
                                  <p className="text-xs text-zinc-400">{app.email}</p>
                                </div>
                              </div>
                              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize whitespace-nowrap ${APPLICATION_STATUS_BADGE[app.status] || 'bg-zinc-100 text-zinc-500'}`}>
                                {app.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
};

export default MyJobs;
