interface SeverityBadgeProps {
  severity: string;
  size?: 'sm' | 'md';
}

const CONFIG: Record<string, { label: string; className: string; emoji: string }> = {
  critical: {
    label: 'Critical',
    emoji: '🔴',
    className: 'bg-red-900/50 text-red-300 border border-red-700',
  },
  high: {
    label: 'High',
    emoji: '🟠',
    className: 'bg-orange-900/50 text-orange-300 border border-orange-700',
  },
  medium: {
    label: 'Medium',
    emoji: '🟡',
    className: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  },
  low: {
    label: 'Low',
    emoji: '🔵',
    className: 'bg-blue-900/50 text-blue-300 border border-blue-700',
  },
  info: {
    label: 'Info',
    emoji: '⚪',
    className: 'bg-gray-800 text-gray-300 border border-gray-700',
  },
};

export default function SeverityBadge({ severity, size = 'md' }: SeverityBadgeProps) {
  const config = CONFIG[severity.toLowerCase()] ?? CONFIG.info;
  const sizeClass = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-xs px-2 py-1';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClass} ${config.className}`}>
      <span>{config.emoji}</span>
      {config.label}
    </span>
  );
}
