import { MessageCircle } from "lucide-react";
import { contact, type LandingContent } from "@/lib/landing-content";
import { lightButton } from "./buttonStyles";

export default function CtaSection({ content }: { content: LandingContent }) {
  return (
    <section className="relative overflow-hidden bg-slate-950 py-20">
      {/* Faint node/line texture echoing the logo's circuit motif — brand reinforcement, not
          decoration for its own sake. Respects prefers-reduced-motion trivially: it's static. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_60%_at_15%_20%,rgba(8,145,178,0.18),transparent),radial-gradient(45%_55%_at_85%_80%,rgba(37,99,235,0.18),transparent)]"
      />
      <div className="relative mx-auto max-w-4xl space-y-8 px-6 text-center">
        <h2 className="text-balance text-3xl font-bold tracking-tight text-white md:text-5xl">
          {content.cta.headline}
        </h2>
        <p className="mx-auto max-w-2xl text-lg text-slate-400 md:text-xl">{content.cta.subtext}</p>
        <a href={contact.whatsapp} target="_blank" rel="noopener noreferrer" className={lightButton("lg")}>
          <MessageCircle className="size-4" aria-hidden="true" />
          {content.cta.button}
        </a>
      </div>
    </section>
  );
}
