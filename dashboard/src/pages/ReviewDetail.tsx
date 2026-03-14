import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchReviewWithFindings, type ReviewWithFindings, type Finding } from '../lib/firestore';
import SeverityBadge from '../components/SeverityBadge';

function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-hidden">
      <button
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-800/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="mt-0.5 shrink-0">
          <SeverityBadge severity={finding.severity} size="sm" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-100 text-sm">{finding.title}</p>
          <p className="mt-0.5 text-xs text-gray-500 font-mono">
            {finding.file}:{finding.line}
          </p>
        </div>
        <span className="text-gray-600 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="border-t border-gray-800 p-4 space-y-3">
          {finding.owasp_category && (
            <p className="text-xs text-orange-400 font-medium">
              OWASP: {finding.owasp_category}
            </p>
          )}
          <p className="text-sm text-gray-300 leading-relaxed">{finding.body}</p>
          {finding.cve_ids && finding.cve_ids.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {finding.cve_ids.map((id) => (
                <span key={id} className="rounded bg-gray-800 px-2 py-0.5 text-xs text-red-400 font-mono">
                  {id}
                </span>
              ))}
            </div>
          )}
          {finding.suggestion && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Suggested Fix
              </p>
              <pre className="overflow-x-auto rounded bg-gray-950 p-3 text-xs text-green-400 border border-gray-800">
                {finding.suggestion}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<ReviewWithFindings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetchReviewWithFindings(id).then((data) => {
      setReview(data);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400">Review not found.</p>
        <Link to="/" className="mt-4 inline-block text-purple-400 hover:underline text-sm">
          ← Back to overview
        </Link>
      </div>
    );
  }

  // Group findings by file
  const byFile: Record<string, Finding[]> = {};
  for (const f of review.findings) {
    if (!byFile[f.file]) byFile[f.file] = [];
    byFile[f.file].push(f);
  }

  // Sort files: critical findings first
  const sortedFiles = Object.entries(byFile).sort(([, a], [, b]) => {
    const aHasCrit = a.some((f) => f.severity === 'critical') ? -1 : 0;
    const bHasCrit = b.some((f) => f.severity === 'critical') ? -1 : 0;
    return aHasCrit - bHasCrit;
  });

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Link to="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
        ← Back to overview
      </Link>

      {/* Header */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-mono text-gray-500">{review.repo}</p>
            <h1 className="mt-1 text-xl font-bold text-white">
              #{review.pr_number} — {review.pr_title}
            </h1>
            <p className="mt-1 text-sm text-gray-400">
              by <span className="font-mono">@{review.author}</span>
            </p>
          </div>
          <a
            href={review.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:border-purple-500 hover:text-purple-400 transition-colors"
          >
            View PR ↗
          </a>
        </div>

        {/* Stats row */}
        <div className="mt-4 flex flex-wrap gap-4 border-t border-gray-800 pt-4">
          <div className="text-sm">
            <span className="text-gray-500">Total findings: </span>
            <span className="font-semibold text-white">{review.finding_count}</span>
          </div>
          {review.critical_count > 0 && (
            <div className="text-sm">
              <span className="text-gray-500">Critical: </span>
              <span className="font-semibold text-red-400">{review.critical_count}</span>
            </div>
          )}
          <div className="text-sm">
            <span className="text-gray-500">Files affected: </span>
            <span className="font-semibold text-white">{sortedFiles.length}</span>
          </div>
        </div>
      </div>

      {/* Findings grouped by file */}
      {sortedFiles.length === 0 ? (
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-8 text-center">
          <p className="text-2xl mb-2">✅</p>
          <p className="text-gray-300 font-medium">No issues found</p>
          <p className="text-sm text-gray-500 mt-1">This PR looks clean!</p>
        </div>
      ) : (
        sortedFiles.map(([filename, findings]) => (
          <div key={filename}>
            <div className="mb-2 flex items-center gap-2">
              <span className="font-mono text-sm text-gray-300">{filename}</span>
              <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                {findings.length}
              </span>
            </div>
            <div className="space-y-2">
              {findings
                .sort((a, b) => {
                  const order = ['critical', 'high', 'medium', 'low', 'info'];
                  return order.indexOf(a.severity) - order.indexOf(b.severity);
                })
                .map((finding, i) => (
                  <FindingCard key={i} finding={finding} />
                ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
