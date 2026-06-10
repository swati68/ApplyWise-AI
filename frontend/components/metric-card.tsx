import type { LucideIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";


type MetricCardProps = {
  label: string;
  value: string;
  helper: string;
  icon: LucideIcon;
  tone?: "blue" | "emerald" | "coral" | "slate";
};


const toneClasses: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  blue: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
  emerald:
    "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
  coral:
    "bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300",
  slate: "bg-muted text-muted-foreground",
};


export function MetricCard({
  helper,
  icon: Icon,
  label,
  tone = "slate",
  value,
}: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <div className={cn("rounded-md p-2", toneClasses[tone])}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold tracking-normal">{value}</div>
        <p className="mt-2 text-sm text-muted-foreground">{helper}</p>
      </CardContent>
    </Card>
  );
}
