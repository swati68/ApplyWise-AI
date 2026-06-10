import { cn } from "@/lib/utils";


type ProgressBarProps = {
  value: number;
  className?: string;
};


export function ProgressBar({ className, value }: ProgressBarProps) {
  const normalizedValue = Math.max(0, Math.min(value, 100));

  return (
    <div className={cn("h-2 overflow-hidden rounded-full bg-muted", className)}>
      <div
        className="h-full rounded-full bg-primary transition-all"
        style={{ width: `${normalizedValue}%` }}
      />
    </div>
  );
}
