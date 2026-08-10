import React from 'react';
import PublicHeader from '../components/PublicHeader';
import PublicFooter from '../components/PublicFooter';

interface LegalPageProps {
  type: 'privacy' | 'terms' | 'weaving';
}

const linkClass = 'font-semibold text-[#0E7490] hover:text-[#075985]';

const LegalPage: React.FC<LegalPageProps> = ({ type }) => {
  const isPrivacy = type === 'privacy';
  const isWeaving = type === 'weaving';

  const getTitle = () => {
    if (isPrivacy) return 'Privacy Policy';
    if (isWeaving) return 'The Practice of Weaving';
    return 'Terms of Service';
  };

  return (
    <div className="min-h-screen bg-[#F2FBFD] text-slate-900">
      <PublicHeader theme="light" />
      <div className="px-4 py-10 sm:px-6 lg:px-8">
      <main className="mx-auto max-w-3xl rounded-lg border border-slate-200 bg-white p-7 shadow-sm sm:p-9">
        <h1 className="mt-5 text-3xl font-bold text-slate-950">
          {getTitle()}
        </h1>
        <p className="mt-2 text-sm text-slate-500">Pro Prime Series Orb Weaver</p>

        {isWeaving ? (
          <div className="mt-7 space-y-6 text-sm leading-7 text-slate-700">
            <p>
              OrbWeaver performs periodic scans of publicly accessible websites and public information sources. OrbWeaver's 
              scanning system does not collect private customer account information, purchase records, private communications, 
              or other non-public customer data.
            </p>
            <p>
              Information gathered during these periodic scans may be compiled and analyzed across multiple public sources. 
              We call this process <strong>the practice of weaving</strong>—connecting separate pieces of public information 
              to identify broader patterns, relationships, changes, industry trends, and research insights that may not be 
              visible from any single source.
            </p>
            <p>
              The resulting non-personal datasets may be used to study patterns across industries and public systems, improve 
              OrbWeaver's research, retrieval, and interpretation methods, produce comparisons, benchmarks, reports, and 
              analytical tools, preserve historical public information, observe changes over time, and support responsible 
              future research that may not yet exist.
            </p>
            <p>
              OrbWeaver does not continuously monitor individual visitors or customers. Scan data is collected only when an 
              authorized periodic scan is performed.
            </p>
            <p>
              The practice of weaving focuses on non-personal public information concerning organizations, industries, 
              products, services, technologies, public websites, and other appropriate research subjects. It is not intended 
              for personal profiling or the collection of intimate, sensitive, or identifying information about private individuals.
            </p>
            <p>
              OrbWeaver identifies itself honestly when accessing public sources. It does not conceal its crawler identity, 
              impersonate human visitors, bypass authentication, defeat access controls, or evade explicit website restrictions.
            </p>
            <p className="font-semibold text-slate-900">
              The goal is to responsibly preserve and combine useful public knowledge so that broader patterns and future 
              research value may become clearer over time.
            </p>
          </div>
        ) : isPrivacy ? (
          <div className="mt-7 space-y-5 text-sm leading-7 text-slate-700">
            <p>
              Orb Weaver is a local-first Website ORB Intelligence Engine. Customer records, login sessions, carts,
              checkout orders, crawl jobs, reports, and client intelligence packs are used to operate the service and
              provide website intelligence workflows.
            </p>
            <p>
              Information collected may include name, email, phone, address, business details, project domains, crawl
              results, audit reports, cart contents, checkout records, and operational logs required to maintain account
              access and reporting history.
            </p>
            <p>
              Orb Weaver is intended to preserve operator control. Data should remain in the configured backend database
              and local-first storage paths unless the operator deliberately connects third-party services such as Stripe,
              PayPal, Google Analytics, or public hosting infrastructure.
            </p>
            <p>
              Customer data should not be sold. Access should be limited to authorized operators, administrators, and
              service workflows required to fulfill customer requests, maintain records, process checkout, and generate
              reports.
            </p>
          </div>
        ) : (
          <div className="mt-7 space-y-5 text-sm leading-7 text-slate-700">
            <p>
              By using Orb Weaver, customers agree to provide accurate account, contact, business, and billing
              information and to use website crawling and reporting tools only for sites they own, operate, manage, or
              are authorized to review.
            </p>
            <p>
              Orb Weaver reports, workflows, branding, data structures, software, generated materials, and client packs
              are proprietary materials of Pro Prime Series Orb Weaver unless a separate written agreement states
              otherwise.
            </p>
            <p>
              Unauthorized copying, redistribution, resale, scraping, reverse engineering, sublicensing, or derivative
              use of the system or its generated materials is prohibited without written permission.
            </p>
            <p>
              Checkout integrations, payment status, customer records, reports, and crawl activity are maintained in the
              Orb Weaver backend database as the operational record for account and service activity.
            </p>
          </div>
        )}

        <footer className="mt-8 border-t border-slate-200 pt-5 text-xs leading-6 text-slate-500">
          <p>Pro Prime Series Orb Weaver. All rights reserved.</p>
          <nav className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
            <a className={linkClass} href="/sitemap.xml">Site Map</a>
            <a className={linkClass} href="/privacy">Privacy Policy</a>
            <a className={linkClass} href="/terms">Terms</a>
            <a className={linkClass} href="/weaving">Practice of Weaving</a>
            <a className={linkClass} href="https://spruked.com">spruked.com</a>
            <a className={linkClass} href="https://truemarkmint.com">truemarkmint.com</a>
            <a className={linkClass} href="https://certsig.com">certsig.com</a>
            <a className={linkClass} href="https://alphacertsig.com">alphacertsig.com</a>
          </nav>
        </footer>
      </main>
      <PublicFooter />
      </div>
    </div>
  );
};

export default LegalPage;
