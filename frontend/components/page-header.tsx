import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";


type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
};


export function PageHeader({
  action,
  description,
  eyebrow,
  title,
}: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div className="max-w-3xl">
        {eyebrow ? (
          <Badge className="mb-3" variant="secondary">
            {eyebrow}
          </Badge>
        ) : null}
        <h1 className="text-3xl font-semibold tracking-normal text-foreground md:text-4xl">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
          {description}
        </p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
