import { Link } from 'react-router-dom';
import type { Review } from '../lib/firestore';
import SeverityBadge from './SeverityBadge';
import { formatTimestamp } from '../lib/firestore';

interface FindingsTableProps {
  reviews: Review[];
  loading: boolean;
}

export default function FindingsTable({ reviews, loading }: FindingsTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-500">
        <span className="text-4xl mb-3">🔍</span>
        <p className="text-sm">No reviews yet. Open a pull request to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-900 text-gray-400">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Repository</th>
            <th className="px-4 py-3 text-left font-medium">Pull Request</th>
            <th className="px-4 py-3 text-left font-medium">Author</th>
            <th className="px-4 py-3 text-left font-medium">Findings</th>
            <th className="px-4 py-3 text-left font-medium">Critical</th>
            <th className="px-4 py-3 text-left font-medium">Reviewed At</th>
            <th className="px-4 py-3 text-left font-medium"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {reviews.map((review) => (
            <tr key={review.id} className="hover:bg-gray-900/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-300">
                {review.repo}
              </td>
              <td className="px-4 py-3">
                <a
                  href={review.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-purple-400 hover:text-purple-300 hover:underline"
                >
                  #{review.pr_number} — {review.pr_title}
                </a>
              </td>
              <td className="px-4 py-3 text-gray-400">
                <span className="font-mono text-xs">@{review.author}</span>
              </td>
              <td className="px-4 py-3">
                <span className="font-semibold text-white">{review.finding_count}</span>
              </td>
              <td className="px-4 py-3">
                {review.critical_count > 0 ? (
                  <SeverityBadge severity="critical" size="sm" />
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {formatTimestamp(review.created_at)}
              </td>
              <td className="px-4 py-3">
                <Link
                  to={`/review/${review.id}`}
                  className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  View →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
