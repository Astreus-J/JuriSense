import { contact, type LandingContent } from "@/lib/landing-content";
import { PhoneIcon } from "./Icons";

export default function CtaSection({ content }: { content: LandingContent }) {
  return (
    <section className="w-full bg-slate-900 py-20 px-6">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <h2 className="text-white text-3xl md:text-5xl font-bold tracking-tight">
          {content.cta.headline}
        </h2>
        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto">
          {content.cta.subtext}
        </p>
        <a
          href={contact.whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-3 rounded-lg bg-white px-8 py-4 text-base font-bold text-slate-900 hover:bg-slate-100 transition-colors"
        >
          <PhoneIcon className="w-4 h-4" />
          {content.cta.button}
        </a>
      </div>
    </section>
  );
}
