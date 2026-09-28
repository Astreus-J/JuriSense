import { ShieldCheck } from "lucide-react";

import { cn } from "@/lib/cn";

export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 text-foreground", className)}>
      <ShieldCheck className="size-6 shrink-0 text-primary" aria-hidden="true" />
      <span className="text-base font-semibold tracking-tight">JuriSense Gate</span>
    </span>
  );
}
