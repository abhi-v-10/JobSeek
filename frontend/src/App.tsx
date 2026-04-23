import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import JobDetails from './pages/JobDetailPage'
import Messages from './pages/Messages'
import SeekBot from './pages/SeekBot'
import PostJob from './pages/PostJob'
import ProfileSettings from './pages/ProfileSettings'
import Resume from './pages/Resume'
import MyJobs from './pages/MyJobs'

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetails />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/seekbot" element={<SeekBot />} />
          <Route path="/post-job" element={<PostJob />} />
          <Route path="/profile" element={<ProfileSettings />} />
          <Route path="/profile-settings" element={<Navigate to="/profile" replace />} />
          <Route path="/resume" element={<Resume />} />
          <Route path="/my-jobs" element={<MyJobs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
