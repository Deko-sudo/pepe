import bitcoinIcon from "@/assets/market/bitcoin.svg";
import ethereumIcon from "@/assets/market/ethereum.svg";
import xauIcon from "@/assets/market/xau.svg";

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

// Bitcoin and Ethereum vectors are vendored from Simple Icons (CC0-1.0).
const assetIcons: Record<string, string> = {
  BTC: bitcoinIcon,
  ETH: ethereumIcon,
  XAU: xauIcon,
};

export function AssetIcon({ asset, label, size = "md" }: AssetIconProps) {
  const normalized = asset.toUpperCase();
  const icon = assetIcons[normalized];

  return (
    <span className={`asset-mark asset-mark-${normalized.toLowerCase()} ${sizeClasses[size]}`}>
      {icon ? (
        <img src={icon} alt={label} aria-label={label} className="asset-icon-image" />
      ) : (
        <span aria-label={label} role="img" className="flex h-full w-full items-center justify-center rounded-full bg-surface-elevated text-xs font-bold text-text-primary">
          {normalized.slice(0, 3)}
        </span>
      )}
    </span>
  );
}
