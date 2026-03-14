import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { subscribeToRecentReviews, type Review } from '../lib/firestore';
import FindingsTable from '../components/FindingsTable';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${accent ?? 'text-white'}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

export default function Overview() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsub = subscribeToRecentReviews((data) => {
      setReviews(data);
      setLoading(false);
    });
    return unsub;
  }, []);

  // Aggregate stats
  const totalReviews = reviews.length;
  const totalFindings = reviews.reduce((s, r) => s + (r.finding_count ?? 0), 0);
  const criticalCount = reviews.reduce((s, r) => s + (r.critical_count ?? 0), 0);
  const repos = new Set(reviews.map((r) => r.repo)).size;

  // Findings over last 7 days for line chart
  const today = new Date();
  const last7 = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });

  const chartData = last7.map((label, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (6 - i));
    const dayStr = d.toDateString();
    const dayReviews = reviews.filter(
      (r) => r.created_at && new Date(r.created_at.seconds * 1000).toDateString() === dayStr
    );
    return {
      date: label,
      findings: dayReviews.reduce((s, r) => s + (r.finding_count ?? 0), 0),
      reviews: dayReviews.length,
    };
  });

  // Severity breakdown for donut
  const severityData = [
    { name: 'Critical', value: criticalCount, key: 'critical' },
    {
      name: 'High',
      value: reviews.reduce((s, r) => s + (r.high_count ?? 0), 0),
      key: 'high',
    },
    {
      name: 'Other',
      value: totalFindings - criticalCount - reviews.reduce((s, r) => s + (r.high_count ?? 0), 0),
      key: 'medium',
    },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-400">
          Real-time AI code review activity across all connected repositories.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="PRs Reviewed" value={totalReviews} sub="all time" />
        <StatCard label="Total Findings" value={totalFindings} sub="all time" />
        <StatCard
          label="Critical Findings"
          value={criticalCount}
          sub="require immediate action"
          accent={criticalCount > 0 ? 'text-red-400' : 'text-white'}
        />
        <StatCard label="Repos Connected" value={repos} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Line chart */}
        <div className="col-span-2 rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="mb-4 text-sm font-semibold text-gray-300">Findings — Last 7 Days</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#d1d5db' }}
                itemStyle={{ color: '#a78bfa' }}
              />
              <Line
                type="monotone"
                dataKey="findings"
                stroke="#a855f7"
                strokeWidth={2}
                dot={{ fill: '#a855f7', r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Donut chart */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="mb-4 text-sm font-semibold text-gray-300">Severity Breakdown</h2>
          {severityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {severityData.map((entry) => (
                    <Cell key={entry.key} fill={SEVERITY_COLORS[entry.key] ?? '#6b7280'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                  itemStyle={{ color: '#d1d5db' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-48 items-center justify-center text-gray-600 text-sm">
              No findings yet
            </div>
          )}
          <div className="mt-2 space-y-1">
            {severityData.map((entry) => (
              <div key={entry.key} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: SEVERITY_COLORS[entry.key] }}
                  />
                  <span className="text-gray-400">{entry.name}</span>
                </div>
                <span className="text-gray-300 font-medium">{entry.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent reviews table */}
      <div>
        <h2 className="mb-4 text-sm font-semibold text-gray-300">Recent Reviews</h2>
        <FindingsTable reviews={reviews} loading={loading} />
      </div>
    </div>
  );
}
