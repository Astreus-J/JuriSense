import { Plus } from "lucide-react";
import type { LandingContent } from "@/lib/landing-content";
import SectionTitle from "./SectionTitle";

export default function Faq({ content }: { content: LandingContent }) {
  return (
    <section id="faq" className="scroll-mt-20 bg-landing-band py-20">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <SectionTitle eyebrow={content.nav.faq} title={content.faq.title} subtitle={content.faq.subtitle} />
        <div className="mt-12 divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white">
          {content.faq.items.map((faq) => (
            <details key={faq.question} className="group p-5 open:bg-landing-canvas first:rounded-t-2xl last:rounded-b-2xl">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 rounded-md">
                {faq.question}
                <Plus
                  className="size-4 shrink-0 text-slate-400 transition-transform duration-200 group-open:rotate-45"
                  aria-hidden="true"
                />
              </summary>
              <p className="mt-3 leading-relaxed text-slate-600">{faq.answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
