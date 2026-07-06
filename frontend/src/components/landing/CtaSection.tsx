import { contact } from "@/lib/landing-data";
import { PhoneIcon } from "./Icons";

export default function CtaSection() {
  return (
    <section className="w-full bg-slate-900 py-20 px-6">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <h2 className="text-white text-3xl md:text-5xl font-bold tracking-tight">
          Pronto para modernizar seu escritório?
        </h2>
        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto">
          Reduza em até 50% o tempo gasto em tarefas administrativas e transforme sua
          gestão jurídica com o JuriSense.
        </p>
        <a
          href={contact.whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-3 rounded-lg bg-white px-8 py-4 text-base font-bold text-slate-900 hover:bg-slate-100 transition-colors"
        >
          <PhoneIcon className="w-4 h-4" />
          Falar com especialista
        </a>
      </div>
    </section>
  );
}
