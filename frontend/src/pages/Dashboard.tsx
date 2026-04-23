import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import Button from '../components/ui/Button';
import { jobsService } from '../services/jobs';
import type { Job } from '../services/jobs';
import { MapPin, Building, Briefcase, Bookmark, Eye, ArrowRight } from 'lucide-react';

// The dashboard returns wrapper objects, not raw Job objects
interface JobWrapper {
  id: number;
  job: Job;
  status?: string;       // for applications
  created_at?: string;
  viewed_at?: string;
}

interface DashboardResponse {
  recently_applied: JobWrapper[];
  recently_viewed: JobWrapper[];
  starred_jobs: JobWrapper[];
  applied_jobs_count: number;
  saved_jobs_count: number;
}

// Helper: derive a display label from a job
function jobTitle(job: Job) {
  return job.position || job.work || '(Untitled)';
}

const Dashboard = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        // getDashboard returns response.data directly
        const raw = await jobsService.getDashboard() as unknown as DashboardResponse;
        setData(raw);
      } catch (err: any) {
        console.error('Failed to fetch dashboard data', err);
        setError(err.response?.data?.detail || 'Failed to load dashboard.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  const renderJobList = (wrappers: JobWrapper[] = [], emptyMessage: string) => {
    if (!Array.isArray(wrappers) || wrappers.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-10 px-4 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900/50">
          <p className="text-zinc-500 dark:text-zinc-400 mb-5 text-center text-sm">{emptyMessage}</p>
          <div className="w-full max-w-[180px]">
            <Button onClick={() => navigate('/jobs')}>Find jobs</Button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {wrappers.map(wrapper => {
          const job = wrapper.job;
          if (!job) return null;
          return (
            <div
              key={wrapper.id}
              onClick={() => navigate(`/jobs/${job.id}`)}
              className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-shadow cursor-pointer gap-3"
            >
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate">
                  {jobTitle(job)}
                </h3>
                <div className="flex items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400 mt-1 flex-wrap">
                  {job.company && (
                    <span className="flex items-center gap-1"><Building size={13} /> {job.company}</span>
                  )}
                  <span className="flex items-center gap-1"><MapPin size={13} /> {job.location}</span>
                </div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); navigate(`/jobs/${job.id}`); }}
                className="text-sm font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1 hover:underline whitespace-nowrap shrink-0"
              >
                View Details <ArrowRight size={14} />
              </button>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <ProtectedRoute>
      <div className="flex-1 flex flex-col p-4 sm:p-6 max-w-7xl mx-auto w-full">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">Dashboard</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8">Welcome back! Here's an overview of your job search.</p>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-zinc-400">Loading your dashboard…</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-red-500">{error}</div>
        ) : data ? (
          <>
            {/* ── Count cards (non-clickable) ── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-10">
              <div className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-900 shadow-sm flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                  <Briefcase size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Applied Jobs</p>
                  <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">{data.applied_jobs_count}</p>
                </div>
              </div>

              <div className="p-6 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-900 shadow-sm flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0">
                  <Bookmark size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Saved Jobs</p>
                  <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">{data.saved_jobs_count}</p>
                </div>
              </div>
            </div>

            {/* ── Job lists ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
              <div className="flex flex-col">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4 flex items-center gap-2">
                  <Briefcase size={20} className="text-blue-500" /> Recently Applied
                </h2>
                {renderJobList(data.recently_applied, 'No recent applications')}
              </div>

              <div className="flex flex-col">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4 flex items-center gap-2">
                  <Bookmark size={20} className="text-purple-500" /> Saved Jobs
                </h2>
                {renderJobList(data.starred_jobs, 'No saved jobs')}
              </div>
            </div>

            <div className="flex flex-col mb-10">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4 flex items-center gap-2">
                <Eye size={20} className="text-emerald-500" /> Recently Viewed
              </h2>
              {renderJobList(data.recently_viewed, 'No recently viewed jobs')}
            </div>
          </>
        ) : null}
      </div>
    </ProtectedRoute>
  );
};

export default Dashboard;
