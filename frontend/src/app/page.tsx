import Header from "@/components/landing/Header";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import HowItWorks from "@/components/landing/HowItWorks";
import Plans from "@/components/landing/Plans";
import Faq from "@/components/landing/Faq";
import CtaSection from "@/components/landing/CtaSection";
import Footer from "@/components/landing/Footer";

export default function Home() {
  return (
    <div className="bg-white text-gray-900">
      <Header />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Plans />
        <Faq />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
