import Image from "next/image";
import { contact, type LandingContent } from "@/lib/landing-content";

export default function Footer({ content }: { content: LandingContent }) {
  const currentYear = new Date().getFullYear();
  const { footer } = content;

  return (
    <footer className="w-full bg-slate-900 text-slate-400 py-12 px-6 border-t border-slate-800">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          <div className="space-y-5">
            <div className="flex items-center gap-2 text-white text-2xl font-bold">
              <Image
                src="/img/logo.jpg"
                alt="JuriSense logo"
                width={48}
                height={48}
                className="rounded-xl"
              />
              <span>JuriSense</span>
            </div>
            <p>{footer.tagline}</p>
            <div className="flex gap-3">
              <a
                href={contact.social.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                LinkedIn
              </a>
              <a
                href={contact.social.instagram}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                Instagram
              </a>
              <a
                href={contact.social.twitter}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-slate-800 rounded-xl text-white hover:bg-slate-700 text-sm"
              >
                X
              </a>
            </div>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">{footer.productLabel}</h3>
            <ul className="space-y-3">
              <li>
                <a href="#features" className="hover:text-white transition-colors">
                  {content.nav.features}
                </a>
              </li>
              <li>
                <a href="#pricing" className="hover:text-white transition-colors">
                  {content.nav.pricing}
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-white transition-colors">
                  {content.nav.howItWorks}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">{footer.resourcesLabel}</h3>
            <ul className="space-y-3">
              <li>
                <a href="#faq" className="hover:text-white transition-colors">
                  {footer.faqHelp}
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  {footer.privacy}
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  {footer.terms}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-white font-semibold mb-5 text-lg">{footer.contactLabel}</h3>
            <ul className="space-y-3">
              <li className="break-all">{contact.email}</li>
              <li>{contact.phone}</li>
              <li>{contact.location}</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between gap-4 text-sm">
          <p>
            © {currentYear} JuriSense. {footer.rights}
          </p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition-colors">
              {footer.terms}
            </a>
            <a href="#" className="hover:text-white transition-colors">
              {footer.privacy}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
