interface StaleBadgeProps {
  className?: string;
}

export function StaleBadge({ className = "" }: StaleBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-warning/20 px-2 py-0.5 text-xs text-warning ${className}`}
    >
      Устаревшие данные
    </span>
  );
}
