import Image from "next/image";

import { cn } from "@/lib/cn";

export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 text-foreground", className)}>
      <Image src="/img/logo.png" alt="" width={28} height={28} className="size-7 shrink-0 rounded-md" />
      <span className="font-serif text-[16px] font-semibold tracking-tight">JuriSense Gate</span>
    </span>
  );
}
