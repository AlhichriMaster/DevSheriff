import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Overview from './pages/Overview';
import ReviewDetail from './pages/ReviewDetail';
import RealtimeIndicator from './components/RealtimeIndicator';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        {/* Top nav */}
        <header className="border-b border-gray-800 bg-gray-900">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🔍</span>
                <span className="text-xl font-bold text-white">DevSheriff</span>
                <span className="rounded-full bg-purple-900 px-2 py-0.5 text-xs text-purple-300">
                  AI Code Review
                </span>
              </div>
              <nav className="flex items-center gap-6">
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `text-sm font-medium transition-colors ${
                      isActive ? 'text-purple-400' : 'text-gray-400 hover:text-gray-100'
                    }`
                  }
                  end
                >
                  Overview
                </NavLink>
                <RealtimeIndicator />
              </nav>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/review/:id" element={<ReviewDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
