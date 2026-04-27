import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import Button from '../components/ui/Button';
import { jobsService } from '../services/jobs';
import type { Job } from '../services/jobs';
import { MapPin, Building, Briefcase, Bookmark, Eye, ArrowRight, Sparkles, Quote } from 'lucide-react';

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

const QUOTES = [
  { text: "The only way to do great work is to love what you do.", author: "Steve Jobs" },
  { text: "Continuous learning is the minimum requirement for success in any field.", author: "Brian Tracy" },
  { text: "Success is not final, failure is not fatal: it is the courage to continue that counts.", author: "Winston Churchill" },
  { text: "Your career is like a garden. It can hold an assortment of life's transitions that are fertile ground for growth.", author: "Anonymous" },
  { text: "The expert in anything was once a beginner.", author: "Helen Hayes" },
  { text: "Don't wait for opportunity. Create it.", author: "Anonymous" },
  { text: "The beautiful thing about learning is that no one can take it away from you.", author: "B.B. King" },
  { text: "Invest in yourself. It pays the best interest.", author: "Benjamin Franklin" },
  { text: "Dream big and dare to fail.", author: "Norman Vaughan" },
  { text: "Your talent determines what you can do. Your motivation determines how much you are willing to do.", author: "Lou Holtz" },
  { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
  { text: "Opportunity is missed by most people because it is dressed in overalls and looks like work.", author: "Thomas Edison" },
  { text: "Believe you can and you're halfway there.", author: "Theodore Roosevelt" },
  { text: "Hard work beats talent when talent doesn't work hard.", author: "Tim Notke" },
  { text: "I find that the harder I work, the more luck I seem to have.", author: "Thomas Jefferson" },
  { text: "The future depends on what you do today.", author: "Mahatma Gandhi" },
  { text: "It always seems impossible until it's done.", author: "Nelson Mandela" },
  { text: "Everything you’ve ever wanted is on the other side of fear.", author: "George Addair" }
];

const Dashboard = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Pagination states
  const [appliedPage, setAppliedPage] = useState(0);
  const [savedPage, setSavedPage] = useState(0);
  const [viewedPage, setViewedPage] = useState(0);
  const itemsPerPage = 3;

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
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

  const renderJobList = (wrappers: JobWrapper[] = [], emptyMessage: string, page: number, setPage: (p: number) => void) => {
    if (!Array.isArray(wrappers) || wrappers.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-6 px-4 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-900/50">
          <p className="text-zinc-500 dark:text-zinc-400 mb-3 text-center text-sm">{emptyMessage}</p>
          <div className="w-full max-w-[140px]">
            <Button size="sm" onClick={() => navigate('/jobs')}>Find jobs</Button>
          </div>
        </div>
      );
    }

    const start = page * itemsPerPage;
    const paginatedItems = wrappers.slice(start, start + itemsPerPage);
    const totalPages = Math.ceil(wrappers.length / itemsPerPage);

    return (
      <div className="flex flex-col h-full justify-between">
        <div className="space-y-2">
          {paginatedItems.map(wrapper => {
            const job = wrapper.job;
            if (!job) return null;
            return (
              <div
                key={wrapper.id}
                onClick={() => navigate(`/jobs/${job.id}`)}
                className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 border border-border rounded-xl bg-card shadow-sm hover:shadow-md transition-shadow cursor-pointer gap-2 group"
              >
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-foreground group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate text-sm">
                    {jobTitle(job)}
                  </h3>
                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-0.5 flex-wrap">
                    {job.company && (
                      <span className="flex items-center gap-1"><Building size={11} /> {job.company}</span>
                    )}
                    <span className="flex items-center gap-1"><MapPin size={11} /> {job.location}</span>
                  </div>
                </div>
                <div className="text-[11px] font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shrink-0">
                  View <ArrowRight size={11} />
                </div>
              </div>
            );
          })}
        </div>
        
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-3 px-1">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Page {page + 1}/{totalPages}</span>
            <div className="flex gap-1">
              <button 
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="p-1 rounded-md hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-muted-foreground"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" /></svg>
              </button>
              <button 
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 rounded-md hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-muted-foreground"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <ProtectedRoute>
      <div className="min-h-[calc(100vh-64px)] flex flex-col p-4 sm:p-6 max-w-7xl mx-auto w-full overflow-x-hidden overflow-y-auto scrollbar-hide">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-foreground leading-tight">Dashboard</h1>
          <p className="text-xs text-muted-foreground">Welcome back! Here's an overview of your job search.</p>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Loading your dashboard…</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center text-destructive">{error}</div>
        ) : data ? (
          <div className="flex-1 flex flex-col min-h-0">
            {/* ── Count cards ── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div className="p-4 border border-border rounded-2xl bg-card shadow-sm flex items-center gap-4 transition-all hover:shadow-md">
                <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                  <Briefcase size={20} />
                </div>
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Applied Jobs</p>
                  <p className="text-2xl font-bold text-foreground leading-none">{data.applied_jobs_count}</p>
                </div>
              </div>

              <div className="p-4 border border-border rounded-2xl bg-card shadow-sm flex items-center gap-4 transition-all hover:shadow-md">
                <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0">
                  <Bookmark size={20} />
                </div>
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Saved Jobs</p>
                  <p className="text-2xl font-bold text-foreground leading-none">{data.saved_jobs_count}</p>
                </div>
              </div>
            </div>

            {/* ── Job lists ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4 min-h-0">
              <div className="flex flex-col min-h-0">
                <h2 className="text-sm font-bold text-foreground mb-2 flex items-center gap-2">
                  <Briefcase size={14} className="text-blue-500" /> Recently Applied
                </h2>
                {renderJobList(data.recently_applied, 'No recent applications', appliedPage, setAppliedPage)}
              </div>

              <div className="flex flex-col min-h-0">
                <h2 className="text-sm font-bold text-foreground mb-2 flex items-center gap-2">
                  <Bookmark size={14} className="text-purple-500" /> Saved Jobs
                </h2>
                {renderJobList(data.starred_jobs, 'No saved jobs', savedPage, setSavedPage)}
              </div>
            </div>

            {/* ── Lower Section ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0 mb-6">
              <div className="flex flex-col min-h-0">
                <h2 className="text-sm font-bold text-foreground mb-2 flex items-center gap-2">
                  <Eye size={14} className="text-emerald-500" /> Recently Viewed
                </h2>
                {renderJobList(data.recently_viewed, 'No recently viewed jobs', viewedPage, setViewedPage)}
              </div>

              <div className="flex flex-col min-h-0">
                <h2 className="text-sm font-bold text-foreground mb-2 flex items-center gap-2">
                  <Sparkles size={14} className="text-amber-500" /> Daily Motivation
                </h2>
                <div className="flex-1 p-5 rounded-2xl bg-secondary border border-border flex flex-col justify-center relative min-h-[140px]">
                  <div className="relative z-10">
                    <Quote className="w-6 h-6 text-muted-foreground mb-2" />
                    
                    <p className="text-sm md:text-base font-medium leading-relaxed mb-3 text-foreground italic">
                      "{QUOTES[Math.floor(Date.now() / (1000 * 60 * 60 * 24)) % QUOTES.length].text}"
                    </p>
                    
                    <div className="flex items-center gap-2">
                      <div className="h-[1px] w-3 bg-zinc-300 dark:bg-zinc-700"></div>
                      <p className="text-[10px] font-bold text-zinc-500 dark:text-zinc-500 tracking-wider uppercase">
                        {QUOTES[Math.floor(Date.now() / (1000 * 60 * 60 * 24)) % QUOTES.length].author}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </ProtectedRoute>
  );
};

export default Dashboard;
