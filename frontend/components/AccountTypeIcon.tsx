import { CreditCard, Landmark, Wallet, type LucideIcon } from "lucide-react";

const ACCOUNT_TYPE_ICONS: Record<string, LucideIcon> = {
  credit: CreditCard,
  savings: Wallet,
  checking: Landmark,
};

type AccountTypeIconProps = {
  type: string;
  size: number;
  className?: string;
};

export function AccountTypeIcon({ type, size, className }: AccountTypeIconProps) {
  const Icon = ACCOUNT_TYPE_ICONS[type] ?? Landmark;
  return <Icon size={size} className={className} />;
}
