interface AssetIconProps {
  asset: string;
  label: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
};

export function AssetIcon({ asset, label, size = "md" }: AssetIconProps) {
  const normalized = asset.toUpperCase();
  const commonProps = {
    viewBox: "0 0 40 40",
    className: "h-full w-full",
    role: "img" as const,
    "aria-label": label,
  };

  return (
    <span className={`asset-mark ${sizeClasses[size]}`}>
      {normalized === "BTC" ? (
        <svg {...commonProps}>
          <circle cx="20" cy="20" r="19" fill="#f59e0b" />
          <path d="M15.5 10.5v19m5-19v19m-8-15h11.2a4.3 4.3 0 0 1 0 8.6H13m0 0h12a4.2 4.2 0 0 1 0 8.4H12.5" fill="none" stroke="#080b11" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4" transform="translate(0 -1)" />
        </svg>
      ) : null}
      {normalized === "ETH" ? (
        <svg {...commonProps}>
          <circle cx="20" cy="20" r="19" fill="#627eea" />
          <path d="m20 7 8 13-8 4.5L12 20 20 7Zm0 19.2 8-4.4L20 33l-8-11.2 8 4.4Z" fill="#f8faff" />
          <path d="m20 7 8 13-8 4.5V7Zm0 19.2 8-4.4L20 33v-6.8Z" fill="#cbd5ff" />
        </svg>
      ) : null}
      {normalized === "XAU" ? (
        <svg {...commonProps}>
          <circle cx="20" cy="20" r="19" fill="#d7ad4b" />
          <path d="M10.5 27.5h19L26 15H14l-3.5 12.5Z" fill="none" stroke="#090c12" strokeLinejoin="round" strokeWidth="2.2" />
          <path d="M15.2 15 17 10.5h6L24.8 15M14 22h12" fill="none" stroke="#090c12" strokeLinecap="round" strokeWidth="2.2" />
        </svg>
      ) : null}
      {!(["BTC", "ETH", "XAU"] as string[]).includes(normalized) ? (
        <span aria-label={label} role="img" className="flex h-full w-full items-center justify-center rounded-full bg-surface-elevated text-xs font-bold text-text-primary">
          {normalized.slice(0, 3)}
        </span>
      ) : null}
    </span>
  );
}
