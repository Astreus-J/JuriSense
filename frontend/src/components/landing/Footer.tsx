import Image from "next/image";
import { contact, type LandingContent } from "@/lib/landing-content";

export default function Footer({ content }: { content: LandingContent }) {
  const currentYear = new Date().getFullYear();
  const { footer } = content;

  return (
    <footer className="border-t border-slate-800 bg-slate-950 py-12 text-slate-400">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
          <div className="space-y-5">
            <div className="flex items-center gap-2 text-lg font-bold text-white">
              <Image src="/img/logo.png" alt="" width={32} height={32} className="rounded-lg" />
              <span>
                JuriSense <span className="font-medium text-slate-400">Gate</span>
              </span>
            </div>
            <p className="text-sm leading-relaxed">{footer.tagline}</p>
            <div className="flex gap-3">
              <a
                href={contact.social.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-white hover:bg-slate-700"
              >
                LinkedIn
              </a>
              <a
                href={contact.social.instagram}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-white hover:bg-slate-700"
              >
                Instagram
              </a>
              <a
                href={contact.social.twitter}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-white hover:bg-slate-700"
              >
                X
              </a>
            </div>
          </div>

          <div>
            <h3 className="mb-5 text-sm font-semibold text-white">{footer.productLabel}</h3>
            <ul className="space-y-3 text-sm">
              <li>
                <a href="#features" className="transition-colors hover:text-white">
                  {content.nav.features}
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="transition-colors hover:text-white">
                  {content.nav.howItWorks}
                </a>
              </li>
              <li>
                <a href="#pricing" className="transition-colors hover:text-white">
                  {content.nav.pricing}
                </a>
              </li>
              <li>
                <a href="#faq" className="transition-colors hover:text-white">
                  {footer.faqHelp}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="mb-5 text-sm font-semibold text-white">{footer.contactLabel}</h3>
            <ul className="space-y-3 text-sm">
              <li className="break-all">
                <a href={`mailto:${contact.email}`} className="transition-colors hover:text-white">
                  {contact.email}
                </a>
              </li>
              <li>{contact.phone}</li>
              <li>{contact.location}</li>
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-slate-800 pt-8 text-sm">
          <p>
            © {currentYear} JuriSense. {footer.rights}
          </p>
        </div>
      </div>
    </footer>
  );
}
