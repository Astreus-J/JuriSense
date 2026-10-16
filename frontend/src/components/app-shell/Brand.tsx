import Image from "next/image";

import { cn } from "@/lib/cn";

interface BrandProps {
  className?: string;
  /** Uses the logo variant made for dark backgrounds (the always-dark navigation rail). */
  onDark?: boolean;
}

export function Brand({ className, onDark = false }: BrandProps) {
  return (
    <span className={cn("flex items-center gap-2 text-foreground", className)}>
      <Image src={onDark ? "/img/logo-dark.png" : "/img/logo.png"} alt="" width={28} height={28} className="size-7 shrink-0 rounded-md" />
      <span className="font-serif text-[16px] font-semibold tracking-tight">JuriSense Gate</span>
    </span>
  );
}
