import React, { useEffect } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import PublicHeader from '../components/PublicHeader';
import PublicFooter from '../components/PublicFooter';

const useCases = [
  ['Product discovery', 'Help visitors understand options, compare relevant products, identify requirements, and move toward the right choice.'],
  ['Sales and conversion', 'Answer questions at the moment of consideration, guide visitors to relevant offers, explain next steps, and reduce uncertainty before abandonment.'],
  ['Forms and applications', 'Explain requirements, clarify confusing fields, and guide visitors through each stage so applications become supported journeys.'],
  ['Bookings and appointments', 'Help visitors identify the correct service, understand requirements, and move into the appropriate approved booking pathway.'],
  ['Customer support', 'Connect questions to the correct answer, policy, account pathway, document, or support action—then escalate with context when needed.'],
  ['Onboarding', 'Welcome new customers, introduce important features, guide setup, and create a structured path through the first experience.'],
  ['Guided website tours', 'Lead visitors through products, services, facilities, campaigns, resources, or platform features while preserving context.'],
  ['Complex decisions', 'Maintain direction across policies, options, forms, calculators, documents, and account processes when one page is not enough.'],
];

const industries = ['Financial services', 'Healthcare navigation', 'Education', 'Property and real estate', 'Travel and hospitality', 'Professional services', 'Retail and e-commerce', 'Membership organizations', 'Government and public services', 'Software and digital platforms'];

const PublicUseCases: React.FC = () => {
  useEffect(() => { document.title = 'Use Cases | ORB Weaver'; }, []);

  return <main data-orb-target="tour-use-cases" className="ow-campaign-page min-h-screen overflow-hidden">
    <PublicHeader theme="dark" />
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <section className="grid min-h-[590px] items-center gap-12 py-20 lg:grid-cols-[1fr_.82fr] lg:py-28">
        <div><p className="ow-feature-kicker">EVERY VISITOR ARRIVES WITH A GOAL.</p><h1 className="mt-6 max-w-3xl text-6xl font-black leading-[.92] sm:text-8xl">Weaver helps them <em className="font-serif font-normal text-[#268c7b]">reach it.</em></h1><p className="mt-8 max-w-2xl text-lg leading-8 text-[#40525b]">From first questions to complex multi-page decisions, Weaver turns fragmented website interactions into guided journeys.</p><div className="mt-9 flex flex-wrap gap-3"><a className="ow-feature-button ow-feature-button-primary" href="#use-cases">Find your use case <ArrowRight size={16} /></a><a className="ow-feature-button ow-feature-button-quiet" href="https://campaign.orbweaver.spruked.com/roi-calculator">Calculate ROI <ArrowRight size={16} /></a></div></div>
        <div className="overflow-hidden border border-black/15 bg-[#e6e5dd] p-5"><img src="/orbweaver1600.png" alt="ORB Weaver moving forward as an intelligent website presence" className="h-[370px] w-full object-cover object-center mix-blend-multiply" /><p className="mt-4 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.16em] text-[#268c7b]"><span className="h-2 w-2 rounded-full bg-[#c2ff4f]" /> A business-facing presence built to guide the journey forward</p></div>
      </section>
      <section id="use-cases" className="scroll-mt-20 border-t border-black/20 py-20 sm:py-28"><div className="max-w-3xl"><p className="ow-feature-kicker">WHERE WEAVER WORKS</p><h2 className="mt-5 text-4xl font-black tracking-[-.055em] sm:text-6xl">The website journey is the use case.</h2><p className="mt-5 text-lg leading-8 text-[#40525b]">Weaver is built for the moments where visitors need context, direction, and confidence—not another warehouse of links.</p></div><div className="mt-12 grid gap-0 border-t border-black/20 sm:grid-cols-2">{useCases.map(([title, body], index) => <article key={title} data-orb-target={`use-case-${index + 1}`} className="border-b border-black/20 py-7 sm:nth-[odd]:border-r sm:nth-[odd]:pr-8 sm:nth-[even]:pl-8"><div className="flex gap-4"><span className="font-serif text-2xl text-[#268c7b]">0{index + 1}</span><div><h3 className="text-2xl font-bold tracking-[-.03em]">{title}</h3><p className="mt-3 max-w-xl leading-7 text-[#40525b]">{body}</p></div></div></article>)}</div></section>
      <section className="border-t border-black/20 py-20 sm:py-28"><div className="grid gap-12 lg:grid-cols-[.7fr_1.3fr]"><div><p className="ow-feature-kicker">INDUSTRY APPLICATIONS</p><h2 className="mt-5 text-4xl font-black tracking-[-.055em] sm:text-6xl">Built around the website you already operate.</h2></div><div className="grid gap-0 sm:grid-cols-2">{industries.map((industry) => <div key={industry} className="flex items-center gap-3 border-b border-black/15 py-4 text-sm font-semibold"><Check size={16} className="text-[#268c7b]" />{industry}</div>)}</div></div></section>
      <section className="mb-20 bg-[#10191b] px-7 py-16 text-[#f2f0e8] sm:mb-28 sm:px-14"><p className="ow-feature-kicker !text-[#c2ff4f]">YOUR WEBSITE HAS VISITORS.</p><h2 className="mt-5 max-w-4xl text-4xl font-black tracking-[-.055em] sm:text-6xl">How many of them are losing the path?</h2><p className="mt-5 max-w-2xl text-lg leading-8 text-[#c7d3cc]">A living, website-aware presence built to explain, guide, request permission, and verify action.</p><div className="mt-8 flex flex-wrap gap-3"><a className="ow-feature-button ow-feature-button-primary" href="https://campaign.orbweaver.spruked.com/roi-calculator">Calculate Website ROI <ArrowRight size={16} /></a><a className="ow-feature-button ow-feature-button-quiet" href="/founding-beta">Discuss an early deployment <ArrowRight size={16} /></a></div></section>
    </div>
    <PublicFooter />
  </main>;
};

export default PublicUseCases;
