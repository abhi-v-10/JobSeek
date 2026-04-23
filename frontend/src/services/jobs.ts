import api from '../lib/axios';

export interface Job {
  id: string | number;
  // Corporate
  company: string;
  position: string;
  type: string;           // employment type: full_time | part_time
  required_experience_years?: number;
  required_experience_fields?: string;
  salary_min?: number;
  salary_max?: number;
  // Domestic
  work: string;
  daily_work_time?: number;
  hourly_wage?: string;
  // Common
  job_type: string;       // corporate | domestic
  location: string;
  status: string;
  description?: string;
  work_mode?: string;     // onsite | remote | hybrid
  posted_by?: number;
  posted_by_username?: string;
  // Interaction counts
  applied_count: number;
  viewed_count: number;
  saved_count: number;
  is_saved?: boolean;
  is_applied?: boolean;
  is_own_job?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Applicant {
  id: number;
  username: string;
  email: string;
  full_name: string;
  status: string;
  created_at: string;
}

export interface MyJob extends Job {
  applicants: Applicant[];
}

export interface DashboardData {
  recently_applied: { id: number; job: Job; status?: string; created_at?: string }[];
  recently_viewed: { id: number; job: Job; viewed_at?: string }[];
  starred_jobs: { id: number; job: Job; created_at?: string }[];
  applied_jobs_count: number;
  saved_jobs_count: number;
}

export interface PostJobPayload {
  job_type: 'corporate' | 'domestic';
  location: string;
  description?: string;
  work_mode?: string;
  // Corporate
  company?: string;
  position?: string;
  type?: string;
  salary_min?: number;
  salary_max?: number;
  required_experience_years?: number;
  required_experience_fields?: string;
  // Domestic
  work?: string;
  daily_work_time?: number;
  hourly_wage?: string;
}

export interface EligibilityData {
  eligible: boolean;
  missing_fields: string[];
  job_type: string;
}

export const jobsService = {
  getDashboard: async (): Promise<DashboardData> => {
    const response = await api.get('/jobs/dashboard/');
    return response.data;
  },

  getJobs: async (): Promise<Job[]> => {
    const response = await api.get('/jobs/');
    return response.data.results || response.data;
  },

  getJobDetails: async (id: string | number): Promise<Job> => {
    const response = await api.get(`/jobs/${id}/`);
    return response.data;
  },

  getMyJobs: async (): Promise<MyJob[]> => {
    const response = await api.get('/jobs/my-jobs/');
    return response.data;
  },

  postJob: async (payload: PostJobPayload): Promise<Job> => {
    const response = await api.post('/jobs/', payload);
    return response.data;
  },

  updateJob: async (id: string | number, payload: Partial<PostJobPayload>): Promise<Job> => {
    const response = await api.patch(`/jobs/${id}/edit/`, payload);
    return response.data;
  },

  getApplyEligibility: async (id: string | number): Promise<EligibilityData> => {
    const response = await api.get(`/jobs/${id}/apply-eligibility/`);
    return response.data;
  },

  applyForJob: async (id: string | number, consent: boolean = true, message: string = ''): Promise<{ application: object; counts: object; conversation_id: number }> => {
    const response = await api.post(`/jobs/${id}/apply/`, { consent, message });
    return response.data;
  },

  viewJob: async (id: string | number): Promise<{ viewed_job: object; counts: object }> => {
    const response = await api.post(`/jobs/${id}/view/`);
    return response.data;
  },

  saveJob: async (id: string | number): Promise<{ saved_job: object; counts: object }> => {
    const response = await api.post(`/jobs/${id}/save/`);
    return response.data;
  },

  unsaveJob: async (id: string | number): Promise<{ detail: string; counts: object }> => {
    const response = await api.delete(`/jobs/${id}/save/`);
    return response.data;
  },
};
