import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import { jobsService } from '../services/jobs';
import type { PostJobPayload } from '../services/jobs';
import api from '../lib/axios';
import { Briefcase, Home, Settings, ChevronDown, X } from 'lucide-react';

// ─── Shared twin-button styles ─────────────────────────────────────────────
// Left button: outline only → hover fills
const btnOutline = "flex-1 py-2.5 px-5 text-sm font-semibold rounded-xl border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer";
// Right button: filled → hover removes fill, shows border only
const btnFilled = "flex-1 py-2.5 px-5 text-sm font-semibold rounded-xl border-2 border-zinc-900 dark:border-zinc-50 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:bg-transparent dark:hover:text-zinc-50 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer";

// ─── Positions list ─────────────────────────────────────────────────────────
const CORPORATE_POSITIONS = [
  'Software Developer', 'Software Designer', 'Full-Stack Developer',
  'Frontend Developer', 'Backend Developer', 'Mobile Developer',
  'Embedded Systems Engineer', 'Machine Learning Engineer', 'AI Engineer',
  'UI/UX Designer', 'Graphic Designer', 'Motion Designer', 'Product Designer',
  'Product Manager', 'Project Manager', 'Engineering Manager', 'CTO',
  'Data Scientist', 'Data Analyst', 'Data Engineer', 'BI Developer',
  'DevOps Engineer', 'Cloud Engineer', 'Site Reliability Engineer',
  'Network Engineer', 'System Administrator', 'Security Engineer',
  'Quality Assurance Engineer', 'QA Lead',
  'Business Analyst', 'Operations Manager', 'Strategy Analyst',
  'HR Manager', 'Talent Acquisition Specialist', 'Office Assistant',
  'Administrative Assistant', 'Receptionist', 'Executive Assistant',
  'Marketing Manager', 'Digital Marketing Specialist', 'Content Writer',
  'SEO Specialist', 'Sales Executive', 'Account Manager', 'Brand Manager',
  'Financial Analyst', 'Accountant', 'CFO',
  'Legal Advisor', 'Compliance Officer',
  'Customer Support Representative', 'Technical Support Specialist',
];

const DOMESTIC_WORK_TYPES = [
  'Gardening', 'Baby Sitting', 'Pet Sitting / Pet Care', 'Day Care / Child Care',
  'House Cleaning', 'Cooking / Chef', 'Elder Care', 'Laundry',
  'Driver / Chauffeur', 'Security Guard', 'Plumbing', 'Electrical Work',
  'Painting', 'Carpentry', 'General Maintenance', 'Other',
];

// ─── Salary helper ──────────────────────────────────────────────────────────
function parseSalary(raw: string): number | undefined {
  const n = parseFloat(raw.replace(/,/g, '').trim());
  if (isNaN(n)) return undefined;
  return n < 1000 ? n * 1000 : n;
}

// ─── Searchable position dropdown ──────────────────────────────────────────
function PositionSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const filtered = CORPORATE_POSITIONS.filter(p => p.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl text-left text-zinc-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
      >
        <span className={value ? '' : 'text-zinc-500 dark:text-zinc-400'}>{value || 'Select a position'}</span>
        <ChevronDown size={18} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute z-50 w-full mt-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-xl shadow-xl overflow-hidden">
          <div className="p-2 border-b border-zinc-100 dark:border-zinc-800">
            <input
              autoFocus type="text" placeholder="Search positions…"
              value={search} onChange={e => setSearch(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-sm text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none"
            />
          </div>
          <ul className="max-h-56 overflow-y-auto">
            {filtered.length === 0
              ? <li className="px-4 py-3 text-sm text-zinc-400">No positions found</li>
              : filtered.map(pos => (
                <li key={pos}>
                  <button
                    type="button"
                    onClick={() => { onChange(pos); setOpen(false); setSearch(''); }}
                    className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${value === pos ? 'bg-blue-600 text-white' : 'text-zinc-800 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}
                  >
                    {pos}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Skills chip input ──────────────────────────────────────────────────────
function ExperienceFieldsInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [input, setInput] = useState('');
  const chips = value ? value.split(',').map(s => s.trim()).filter(Boolean) : [];

  const addChip = (text: string) => {
    const t = text.trim();
    if (!t || chips.includes(t)) return;
    onChange([...chips, t].join(', '));
    setInput('');
  };
  const removeChip = (chip: string) => onChange(chips.filter(c => c !== chip).join(', '));

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-2">
        {chips.map(chip => (
          <span key={chip} className="flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
            {chip}
            <button type="button" onClick={() => removeChip(chip)}><X size={12} /></button>
          </span>
        ))}
      </div>
      <input
        type="text" value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addChip(input); } }}
        onBlur={() => { if (input.trim()) addChip(input); }}
        placeholder="Type a skill and press Enter (e.g. React, Django)"
        className="w-full px-4 py-3 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
      />
      <p className="text-xs text-zinc-400 mt-1">Press Enter or comma to add each skill</p>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────
type Step = 'pick' | 'corporate' | 'domestic';

const PostJob = () => {
  const navigate = useNavigate();
  const [userType, setUserType] = useState<string | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [step, setStep] = useState<Step>('pick');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [successId, setSuccessId] = useState<string | number | null>(null);

  const [corp, setCorp] = useState({
    company: '', position: '', location: '', salary_min: '', salary_max: '',
    type: 'full_time', required_experience_years: '', required_experience_fields: '',
    description: '', work_mode: 'onsite',
  });
  const [dom, setDom] = useState({
    work: '', daily_work_time: '', location: '', hourly_wage: '',
    description: '', work_mode: 'onsite',
  });

  useEffect(() => {
    api.get('/users/profile/')
      .then(res => setUserType(res.data.user_type))
      .catch(() => setUserType(null))
      .finally(() => setLoadingProfile(false));
  }, []);

  const handleSubmitCorporate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    setIsSubmitting(true);
    try {
      const payload: PostJobPayload = {
        job_type: 'corporate',
        company: corp.company, position: corp.position, location: corp.location,
        type: corp.type, description: corp.description, work_mode: corp.work_mode,
        salary_min: parseSalary(corp.salary_min), salary_max: parseSalary(corp.salary_max),
        required_experience_years: corp.required_experience_years ? parseInt(corp.required_experience_years) : undefined,
        required_experience_fields: corp.required_experience_fields || undefined,
      };
      const job = await jobsService.postJob(payload);
      setSuccessId(job.id);
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to post job.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitDomestic = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    setIsSubmitting(true);
    try {
      const payload: PostJobPayload = {
        job_type: 'domestic', location: dom.location, work: dom.work,
        description: dom.description, work_mode: dom.work_mode,
        daily_work_time: dom.daily_work_time ? parseInt(dom.daily_work_time) : undefined,
        hourly_wage: dom.hourly_wage || undefined,
      };
      const job = await jobsService.postJob(payload);
      setSuccessId(job.id);
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Failed to post job.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputCls = "w-full px-4 py-3 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors";
  const labelCls = "block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2";

  const resetAndPick = () => {
    setSuccessId(null); setStep('pick'); setSubmitError('');
    setCorp({ company:'',position:'',location:'',salary_min:'',salary_max:'',type:'full_time',required_experience_years:'',required_experience_fields:'',description:'',work_mode:'onsite' });
    setDom({ work:'',daily_work_time:'',location:'',hourly_wage:'',description:'',work_mode:'onsite' });
  };

  // ── Success ─────────────────────────────────────────────────────────────
  if (successId !== null) {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-6">
            <Briefcase size={36} className="text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Job Posted!</h2>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8 max-w-sm">Your job has been published and seekers can now apply.</p>
          <div className="flex gap-3 w-full max-w-xs">
            <button onClick={() => navigate(`/jobs/${successId}`)} className={btnOutline}>View Job</button>
            <button onClick={resetAndPick} className={btnFilled}>Post Another</button>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (loadingProfile) {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex items-center justify-center"><p className="text-zinc-400">Loading…</p></div>
      </ProtectedRoute>
    );
  }

  // ── Not a poster ─────────────────────────────────────────────────────────
  if (userType !== 'poster') {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-20 h-20 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mb-6">
            <Briefcase size={36} className="text-amber-600 dark:text-amber-400" />
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Access Restricted</h2>
          <p className="text-zinc-500 dark:text-zinc-400 mb-2 max-w-sm">
            Only <span className="font-semibold text-amber-600 dark:text-amber-400">Job Poster</span> accounts can post jobs.
          </p>
          <p className="text-zinc-400 mb-8 max-w-sm text-sm">Switch your account type in Profile Settings.</p>
          <div className="flex gap-3 w-full max-w-xs">
            <button onClick={() => navigate('/profile')} className={btnOutline + ' flex items-center justify-center gap-2'}>
              <Settings size={15} /> Settings
            </button>
            <button onClick={() => navigate('/jobs')} className={btnFilled}>Browse Jobs</button>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // ── Step 1: Pick type ────────────────────────────────────────────────────
  if (step === 'pick') {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex flex-col p-6 max-w-2xl mx-auto w-full">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Post a Job</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mb-10">Which type of job do you want to post?</p>
          <div className="space-y-4">
            <button
              onClick={() => setStep('corporate')}
              className="w-full flex items-center gap-5 p-6 bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500 rounded-2xl transition-all group shadow-sm hover:shadow-md text-left"
            >
              <div className="w-14 h-14 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0 group-hover:scale-110 transition-transform">
                <Briefcase size={28} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">Corporate Job</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Full-time or part-time positions in companies</p>
              </div>
            </button>
            <button
              onClick={() => setStep('domestic')}
              className="w-full flex items-center gap-5 p-6 bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 hover:border-purple-500 dark:hover:border-purple-500 rounded-2xl transition-all group shadow-sm hover:shadow-md text-left"
            >
              <div className="w-14 h-14 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0 group-hover:scale-110 transition-transform">
                <Home size={28} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">Domestic Job</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Household and personal service work</p>
              </div>
            </button>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // ── Step 2a: Corporate form ──────────────────────────────────────────────
  if (step === 'corporate') {
    return (
      <ProtectedRoute>
        <div className="flex-1 flex flex-col p-6 max-w-2xl mx-auto w-full">
          <button onClick={() => setStep('pick')} className="self-start text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50 mb-6 transition-colors">
            ← Back
          </button>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <Briefcase size={22} />
            </div>
            <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">Corporate Job</h1>
          </div>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8">Work in corporate companies</p>

          <form onSubmit={handleSubmitCorporate} className="space-y-6">
            <div>
              <label className={labelCls}>Company Name <span className="text-red-500">*</span></label>
              <input required className={inputCls} placeholder="e.g. Acme Corp" value={corp.company} onChange={e => setCorp(p => ({ ...p, company: e.target.value }))} />
            </div>
            <div>
              <label className={labelCls}>Position <span className="text-red-500">*</span></label>
              <PositionSelect value={corp.position} onChange={v => setCorp(p => ({ ...p, position: v }))} />
            </div>
            <div>
              <label className={labelCls}>Location <span className="text-red-500">*</span></label>
              <input required className={inputCls} placeholder="e.g. Mumbai, India" value={corp.location} onChange={e => setCorp(p => ({ ...p, location: e.target.value }))} />
            </div>
            <div>
              <label className={labelCls}>Employment Type</label>
              <select className={inputCls} value={corp.type} onChange={e => setCorp(p => ({ ...p, type: e.target.value }))}>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Work Mode</label>
              <select className={inputCls} value={corp.work_mode} onChange={e => setCorp(p => ({ ...p, work_mode: e.target.value }))}>
                <option value="onsite">On-site</option>
                <option value="remote">Remote / Work from Home</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Salary Range</label>
              <div className="flex gap-3">
                <input className={inputCls} placeholder="Min (e.g. 15 or 15000)" value={corp.salary_min} onChange={e => setCorp(p => ({ ...p, salary_min: e.target.value }))} />
                <div className="flex items-center text-zinc-400 font-bold">–</div>
                <input className={inputCls} placeholder="Max (e.g. 25 or 25000)" value={corp.salary_max} onChange={e => setCorp(p => ({ ...p, salary_max: e.target.value }))} />
              </div>
              <p className="text-xs text-zinc-400 mt-1">Values under 1000 are treated as thousands (₹).</p>
            </div>
            <div>
              <label className={labelCls}>Required Experience (years)</label>
              <input type="number" min="0" max="40" className={inputCls} placeholder="e.g. 3" value={corp.required_experience_years} onChange={e => setCorp(p => ({ ...p, required_experience_years: e.target.value }))} />
            </div>
            <div>
              <label className={labelCls}>Required Skills / Tech Stack</label>
              <ExperienceFieldsInput value={corp.required_experience_fields} onChange={v => setCorp(p => ({ ...p, required_experience_fields: v }))} />
            </div>
            <div>
              <label className={labelCls}>Job Description</label>
              <textarea rows={4} className={inputCls} placeholder="Describe the role, responsibilities, perks…" value={corp.description} onChange={e => setCorp(p => ({ ...p, description: e.target.value }))} />
            </div>

            {submitError && <p className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 px-4 py-3 rounded-xl">{submitError}</p>}

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setStep('pick')} className={btnOutline}>Back</button>
              <button
                type="submit"
                disabled={isSubmitting || !corp.company || !corp.position || !corp.location}
                className={btnFilled}
              >
                {isSubmitting ? 'Posting…' : 'Post Job'}
              </button>
            </div>
          </form>
        </div>
      </ProtectedRoute>
    );
  }

  // ── Step 2b: Domestic form ───────────────────────────────────────────────
  return (
    <ProtectedRoute>
      <div className="flex-1 flex flex-col p-6 max-w-2xl mx-auto w-full">
        <button onClick={() => setStep('pick')} className="self-start text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-50 mb-6 transition-colors">
          ← Back
        </button>
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400">
            <Home size={22} />
          </div>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">Domestic Job</h1>
        </div>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8">Post domestic work opportunities</p>

        <form onSubmit={handleSubmitDomestic} className="space-y-6">
          <div>
            <label className={labelCls}>Type of Work <span className="text-red-500">*</span></label>
            <select required className={inputCls} value={dom.work} onChange={e => setDom(p => ({ ...p, work: e.target.value }))}>
              <option value="">Select work type</option>
              {DOMESTIC_WORK_TYPES.map(w => <option key={w} value={w}>{w}</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>Daily Work Hours</label>
            <input type="number" min="1" max="24" className={inputCls} placeholder="e.g. 4" value={dom.daily_work_time} onChange={e => setDom(p => ({ ...p, daily_work_time: e.target.value }))} />
          </div>
          <div>
            <label className={labelCls}>Location <span className="text-red-500">*</span></label>
            <input required className={inputCls} placeholder="e.g. Bandra, Mumbai" value={dom.location} onChange={e => setDom(p => ({ ...p, location: e.target.value }))} />
          </div>
          <div>
            <label className={labelCls}>Work Mode</label>
            <select className={inputCls} value={dom.work_mode} onChange={e => setDom(p => ({ ...p, work_mode: e.target.value }))}>
              <option value="onsite">On-site</option>
              <option value="remote">Remote / Work from Home</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </div>
          <div>
            <label className={labelCls}>Hourly Wage</label>
            <input className={inputCls} placeholder="e.g. 500 - 600 per hour" value={dom.hourly_wage} onChange={e => setDom(p => ({ ...p, hourly_wage: e.target.value }))} />
          </div>
          <div>
            <label className={labelCls}>Job Description</label>
            <textarea rows={4} className={inputCls} placeholder="Describe the work, schedule, requirements…" value={dom.description} onChange={e => setDom(p => ({ ...p, description: e.target.value }))} />
          </div>

          {submitError && <p className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 px-4 py-3 rounded-xl">{submitError}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setStep('pick')} className={btnOutline}>Back</button>
            <button
              type="submit"
              disabled={isSubmitting || !dom.work || !dom.location}
              className={btnFilled}
            >
              {isSubmitting ? 'Posting…' : 'Post Job'}
            </button>
          </div>
        </form>
      </div>
    </ProtectedRoute>
  );
};

export default PostJob;
