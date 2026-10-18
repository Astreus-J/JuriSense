import type { LucideIcon } from "lucide-react";
import { CheckCircle2, MessageCircle, ShieldCheck, SlidersHorizontal, UploadCloud } from "lucide-react";
import type { LandingContent } from "@/lib/landing-content";
import SectionTitle from "./SectionTitle";

const ICONS: Record<string, LucideIcon> = {
  "message-circle": MessageCircle,
  "sliders-horizontal": SlidersHorizontal,
  "upload-cloud": UploadCloud,
  "check-circle-2": CheckCircle2,
  "shield-check": ShieldCheck,
};

export default function HowItWorks({ content }: { content: LandingContent }) {
  const { steps, stepLabel } = content.howItWorks;

  return (
    <section id="how-it-works" className="scroll-mt-20 bg-landing-band py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionTitle
          eyebrow={content.howItWorks.eyebrow}
          title={content.howItWorks.title}
          subtitle={content.howItWorks.subtitle}
        />

        <ol className="relative mt-16 grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-5">
          {/* The connecting rail is purely decorative (aria-hidden) and only rendered at the
              breakpoint where steps actually sit in a single row. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-[10%] right-[10%] top-6 hidden h-px bg-slate-200 lg:block"
          />
          {steps.map((item) => {
            const Icon = ICONS[item.icon] ?? CheckCircle2;
            return (
              <li key={item.step} className="relative flex flex-col items-center text-center">
                <div className="relative z-10 flex size-12 items-center justify-center rounded-full border-2 border-blue-600 bg-white text-blue-600">
                  <Icon className="size-5" aria-hidden="true" />
                </div>
                <span className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {stepLabel} {item.step}
                </span>
                <h3 className="mt-1 font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.description}</p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
