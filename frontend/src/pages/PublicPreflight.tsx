import React, { FormEvent, useMemo, useState } from 'react';
import PublicHeader from '../components/PublicHeader';
import { api, PublicPreflightReport } from '../services/api';

const publicScanAreas = [
  ['Website structure', 'Public pages, navigation, links, sitemap signals, robots rules, and visible website patterns.'],
  ['Visitor pathways', 'Products, services, contact options, forms, booking routes, cart and checkout routes, account routes, and public destinations where visitors may need guidance.'],
  ['Installation fit', 'A practical readiness result: ready for a Basic Website ORB, needs review before installation, or not recommended yet.'],
];

const preflightLimits = [
  'Not a full technical audit.',
  'Not a penetration test.',
  'Not a legal accessibility certification.',
  'Not a private-page scan.',
  'Not an installation.',
  'No automatic website modification.',
];

const readinessResults = [
  ['Ready for a Basic Website ORB', 'The public site appears to have enough visible structure and visitor pathways to begin ORB planning.'],
  ['Needs review before installation', 'Orb Weaver found useful public signals, but the site needs closer review before an ORB recommendation is made.'],
  ['Not recommended yet', 'The public site may need clearer pages, pathways, or readiness work before a website guide can serve visitors reliably.'],
];

const customerReceives = [
  'A plain-language readiness outcome.',
  'A fit score based on live public pages read during this scan.',
  'Visible reasons behind the result.',
  'Basic public signals such as pages read, sitemap and robots detection, forms, products, booking, and warnings when available.',
  'Recommended next steps without requiring an account.',
];

const PublicPreflight: React.FC = () => {
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [report, setReport] = useState<PublicPreflightReport | null>(null);
  const [error, setError] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const scanSignals = useMemo(() => {
    if (!report) {
      return {
        hasAuth: false,
        hasCheckout: false,
        hasIncompletePages: false,
      };
    }

    const scanText = `${report.summary} ${report.reasons.join(' ')}`.toLowerCase();

    return {
      hasAuth: /auth|login|account|session|member/.test(scanText),
      hasCheckout: /checkout|e-commerce|ecommerce|payment|cart|purchase/.test(scanText),
      hasIncompletePages: /placeholder|unfinished|temporary|coming soon|draft/.test(scanText),
    };
  }, [report]);

  const fitExplanation = useMemo(() => {
    if (!report) return '';

    if (report.fit_score >= 80) {
      return 'Your public website appears to provide a strong foundation for a Basic Visitor ORB. Orb Weaver found enough visible structure, public pathways, and usable site context to begin planning guided visitor support.';
    }

    if (report.fit_score >= 60) {
      return 'Your public website appears to have a workable foundation for an ORB, but some visitor pathways or website details should be reviewed before installation is recommended.';
    }

    return 'Your website may need additional public structure, clearer visitor pathways, or a closer review before an ORB can guide visitors reliably.';
  }, [report]);
  const pagesRead = report?.basic_checks.pages_read ?? report?.basic_checks.sample_pages_read ?? 0;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setReport(null);
    setIsRunning(true);

    try {
      setReport(await api.publicPreflight(websiteUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preflight scan failed');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 text-white">
      <PublicHeader theme="dark" />

      <div className="pointer-events-none fixed inset-0 opacity-70">
        <div className="absolute left-1/2 top-24 h-[520px] w-[720px] -translate-x-1/2 rounded-full bg-cyan-400/5 blur-3xl" />
        <div className="absolute right-[12%] top-56 h-64 w-64 rounded-full border border-cyan-400/10" />
        <div className="absolute right-[15%] top-60 h-52 w-52 rounded-full border border-blue-500/10" />
      </div>

      <div className="relative mx-auto w-full max-w-6xl px-6 py-8 md:px-8">
        <section className="flex min-h-[620px] flex-col justify-center py-16">
          <div className="grid items-center gap-12 lg:grid-cols-[1fr_280px]">
            <div>
              <p className="mb-3 text-sm font-semibold tracking-[0.24em] text-cyan-300">
                PUBLIC PREFLIGHT
              </p>

              <h1 className="max-w-3xl text-4xl font-black leading-tight md:text-6xl">
                Run a free ORB readiness scan.
              </h1>

              <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">
                Check whether your website is ready for a Basic Website ORB before creating an account.
                Orb Weaver reviews public website structure, visitor pathways, forms, services, and
                contact options to determine whether an ORB can help visitors safely and usefully.
              </p>

              <form onSubmit={handleSubmit} className="mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
                <input
                  className="min-h-[48px] flex-1 rounded-lg border border-cyan-300/20 bg-white px-4 text-slate-950 outline-none ring-cyan-300/40 focus:ring-4"
                  type="text"
                  value={websiteUrl}
                  onChange={(event) => setWebsiteUrl(event.target.value)}
                  placeholder="https://example.com"
                  aria-label="Website URL"
                  required
                />

                <button
                  className="min-h-[48px] rounded-lg bg-cyan-300 px-6 font-bold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                  type="submit"
                  disabled={isRunning}
                >
                  {isRunning ? 'Scanning...' : 'Run Preflight'}
                </button>
              </form>

              <p className="mt-4 text-sm text-slate-400">
                Public website scan only. No installation. No account required. No changes are made to your website.
              </p>
            </div>

            <div className="relative mx-auto flex h-56 w-56 items-center justify-center lg:mx-0">
              <div className="absolute inset-0 rounded-full border border-cyan-400/10" />
              <div className="absolute inset-5 rounded-full border border-blue-400/15" />
              <div className="absolute inset-10 rounded-full bg-cyan-400/10 blur-xl" />
              <img
                src="/orb-skins/tuxorb.png"
                alt="Orb Weaver Website ORB - intelligent site host ready to guide visitors"
                className="relative z-10 h-40 w-40 rounded-full object-contain drop-shadow-[0_0_28px_rgba(34,211,238,0.42)]"
              />
            </div>
          </div>

          {error && (
            <div className="mt-8 max-w-2xl rounded-lg border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
              {error}
            </div>
          )}

          {report && (
            <section className="mt-10 space-y-6">
              <div className="grid gap-5 rounded-xl border border-cyan-300/25 bg-white/[0.045] p-6 shadow-2xl shadow-cyan-950/40 md:grid-cols-[1fr_250px]">
                <div>
                  <p className="text-sm font-semibold text-cyan-200">{report.outcome_title}</p>
                  <h2 className="mt-2 break-all text-2xl font-bold text-white">{report.site_url}</h2>

                  <div className="mt-5 rounded-lg border border-cyan-300/15 bg-slate-950/50 p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-300">
                      Your result, in plain English
                    </p>
                    <p className="mt-2 text-base leading-relaxed text-slate-100">{fitExplanation}</p>
                  </div>

                  <p className="mt-5 text-slate-300">{report.summary}</p>

                  <div className="mt-5">
                    <p className="text-sm font-bold text-white">What Orb Weaver found</p>
                    <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-200">
                      {report.reasons.slice(0, 5).map((reason) => (
                        <li key={reason} className="flex gap-2">
                          <span className="text-cyan-300">•</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="rounded-xl border border-white/5 bg-slate-900/80 p-5">
                  <p className="text-sm text-slate-400">Fit Score</p>
                  <p className="mt-1 text-5xl font-black text-cyan-200">{report.fit_score}</p>
                  <p className="mt-1 text-sm font-semibold text-cyan-100">
                    {report.fit_score >= 80 ? 'Strong Basic ORB Fit' : report.fit_score >= 60 ? 'Review Recommended' : 'Readiness Work Needed'}
                  </p>

                  <div className="mt-6 border-t border-white/10 pt-4">
                    <p className="text-sm text-slate-400">Install Path</p>
                    <p className="mt-1 break-words text-sm font-semibold text-white">{report.install_path}</p>
                  </div>

                  <div className="mt-5">
                    <p className="text-sm text-slate-400">Live pages read</p>
                    <p className="mt-1 text-xl font-bold text-white">{pagesRead}</p>
                  </div>
                </div>
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <article className="rounded-xl border border-cyan-300/15 bg-slate-900/45 p-5">
                  <p className="text-sm font-bold text-cyan-200">Verified public guidance</p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    A Basic Visitor ORB can be prepared around verified public pages, visible services,
                    contact routes, and other real destinations your visitors can reach.
                  </p>
                </article>

                <article className="rounded-xl border border-cyan-300/15 bg-slate-900/45 p-5">
                  <p className="text-sm font-bold text-cyan-200">Clearer next steps</p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    Instead of making visitors hunt through menus and pages, the ORB can help them
                    find the correct public page, form, service, or contact path.
                  </p>
                </article>

                <article className="rounded-xl border border-cyan-300/15 bg-slate-900/45 p-5">
                  <p className="text-sm font-bold text-cyan-200">No invented answers</p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    Orb Weaver is designed to guide visitors using verified public website context.
                    It should not invent services, prices, policies, or paths your website does not contain.
                  </p>
                </article>
              </div>

              <section className="rounded-xl border border-blue-300/15 bg-blue-950/20 p-6">
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">
                  What this scan means for your visitors
                </p>

                <h3 className="mt-3 text-2xl font-bold text-white">
                  A Website ORB helps visitors reach a real next step.
                </h3>

                <p className="mt-3 max-w-4xl leading-relaxed text-slate-300">
                  The purpose is not to place a generic overlay on your site. The purpose is to
                  prepare an ORB that understands your visible public structure well enough to guide
                  someone toward the right service, product, department, form, page, or contact option.
                </p>

                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {[
                    'Find the right public service, product, or information page.',
                    'Locate visible contact forms, support routes, phone information, or live chat.',
                    'Help visitors understand where to begin when the site presents several choices.',
                    'Guide people toward verified public site destinations instead of vague directions.',
                  ].map((benefit) => (
                    <div key={benefit} className="rounded-lg border border-white/10 bg-slate-950/40 p-4 text-sm text-slate-200">
                      <span className="mr-2 text-cyan-300">✓</span>
                      {benefit}
                    </div>
                  ))}
                </div>
              </section>

              {(scanSignals.hasAuth || scanSignals.hasCheckout || scanSignals.hasIncompletePages) && (
                <section className="rounded-xl border border-amber-300/20 bg-amber-400/[0.06] p-6">
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-amber-200">
                    Important boundaries found during this scan
                  </p>

                  <h3 className="mt-3 text-2xl font-bold text-white">
                    Public guidance and protected actions are handled differently.
                  </h3>

                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    {scanSignals.hasAuth && (
                      <article className="rounded-lg border border-amber-200/10 bg-slate-950/35 p-4">
                        <p className="font-semibold text-amber-100">Protected account areas detected</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-300">
                          Login and account-related routes should remain outside normal public ORB guidance
                          unless they are explicitly reviewed and approved.
                        </p>
                      </article>
                    )}

                    {scanSignals.hasCheckout && (
                      <article className="rounded-lg border border-amber-200/10 bg-slate-950/35 p-4">
                        <p className="font-semibold text-amber-100">Checkout or transaction paths detected</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-300">
                          Transaction-related routes need additional safety rules. The ORB may identify
                          these areas, but it should not automate payment or sensitive purchase actions.
                        </p>
                      </article>
                    )}

                    {scanSignals.hasIncompletePages && (
                      <article className="rounded-lg border border-amber-200/10 bg-slate-950/35 p-4">
                        <p className="font-semibold text-amber-100">Incomplete or placeholder pages detected</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-300">
                          These pages should be reviewed before being added to a public guidance map so
                          visitors are not directed toward unfinished experiences.
                        </p>
                      </article>
                    )}
                  </div>

                  <p className="mt-5 text-sm leading-relaxed text-amber-50/90">
                    This is not necessarily a problem with your website. It is a safety and installation
                    boundary: public visitor guidance is treated differently from login, payment, private,
                    and other sensitive actions.
                  </p>
                </section>
              )}

              <section className="grid gap-6 rounded-xl border border-cyan-300/20 bg-gradient-to-br from-cyan-400/[0.10] to-blue-950/30 p-6 lg:grid-cols-[1.25fr_0.75fr]">
                <div>
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-200">
                    Recommended next step
                  </p>

                  <h3 className="mt-3 text-2xl font-bold text-white">
                    Move from a fit check to a complete ORB plan.
                  </h3>

                  <p className="mt-3 max-w-2xl leading-relaxed text-slate-200">
                    This free preflight confirms whether the public site appears to be a fit. The next
                    step is a deeper readiness review that maps visitor routes, visible targets, page
                    context, and installation boundaries before an ORB is configured.
                  </p>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <a
                      href="/signup?intent=site_review"
                      className="rounded-lg bg-cyan-300 px-5 py-3 text-center text-sm font-bold text-slate-950 transition hover:bg-cyan-200"
                    >
                      Proceed to Site Review
                    </a>

                    <a
                      href="/signup?intent=site_update"
                      className="rounded-lg border border-cyan-200/30 px-5 py-3 text-center text-sm font-bold text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10"
                    >
                      Request a Site Update
                    </a>

                    <a
                      href="/marketplace"
                      className="rounded-lg border border-cyan-200/30 px-5 py-3 text-center text-sm font-bold text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10"
                    >
                      Explore ORB packages
                    </a>
                  </div>

                  <p className="mt-4 text-sm text-cyan-100/80">
                    No monthly subscription is required for a Basic Website ORB to keep guiding visitors.
                  </p>
                </div>

                <div className="rounded-xl border border-white/10 bg-slate-950/40 p-5">
                  <p className="text-sm font-bold text-white">From scan to live ORB</p>

                  <ol className="mt-4 space-y-4 text-sm text-slate-300">
                    <li className="flex gap-3">
                      <span className="font-black text-cyan-300">01</span>
                      <span><strong className="text-white">Free Preflight:</strong> confirm whether the public site appears suitable.</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="font-black text-cyan-300">02</span>
                      <span><strong className="text-white">Readiness Review:</strong> map public site context, visitor paths, and boundaries.</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="font-black text-cyan-300">03</span>
                      <span><strong className="text-white">ORB Configuration:</strong> prepare guidance around the real website, not generic guesses.</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="font-black text-cyan-300">04</span>
                      <span><strong className="text-white">Installation:</strong> activate approved public guidance while protected actions stay governed.</span>
                    </li>
                  </ol>
                </div>
              </section>

              <section className="border-t border-white/10 pt-10">
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">
                  Preflight questions
                </p>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <article className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                    <h3 className="font-bold text-white">Do I need an account to run a preflight?</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-300">
                      No. The public preflight is designed to help determine whether Orb Weaver is worth
                      exploring before you create an account or purchase anything.
                    </p>
                  </article>

                  <article className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                    <h3 className="font-bold text-white">Will this change my website?</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-300">
                      No. The preflight only reviews publicly available website information. It does not
                      install code, publish changes, log in, submit forms, or modify your site.
                    </p>
                  </article>

                  <article className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                    <h3 className="font-bold text-white">What happens if the site needs more work?</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-300">
                      The result will explain whether the site needs review or clearer public pathways
                      before an ORB makes sense. A preflight is a fit check, not a forced sale.
                    </p>
                  </article>

                  <article className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
                    <h3 className="font-bold text-white">Is this the same as a full audit?</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-300">
                      No. The preflight is an initial website fit check. A deeper review prepares
                      richer site context, visitor targets, and an installation recommendation.
                    </p>
                  </article>
                </div>
              </section>
            </section>
          )}

          {!report && (
            <section className="mt-14 space-y-8 border-t border-white/10 pt-10">
              <div className="grid gap-5 md:grid-cols-3">
                {publicScanAreas.map(([title, body]) => (
                  <article key={title} className="rounded-xl border border-cyan-300/15 bg-white/[0.025] p-5">
                    <p className="text-sm font-bold text-cyan-200">{title}</p>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{body}</p>
                  </article>
                ))}
              </div>

              <section className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
                <article className="rounded-xl border border-cyan-300/15 bg-slate-900/45 p-6">
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">What Public Preflight is</p>
                  <h2 className="mt-3 text-2xl font-bold text-white">A no-account public readiness check.</h2>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    Public Preflight is for owners, marketers, operators, and builders who want to know whether a public
                    website has enough visible structure for an embodied website guide. It reviews only publicly accessible
                    information and does not log in, submit forms, install code, or change the website.
                  </p>
                </article>

                <article className="rounded-xl border border-amber-300/20 bg-amber-400/[0.06] p-6">
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-amber-200">Safety boundary</p>
                  <h2 className="mt-3 text-2xl font-bold text-white">No website changes are made.</h2>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    The scan reads public website information only. Private pages, account areas, checkout actions,
                    admin routes, sensitive transactions, and owner-only systems remain outside the public scan boundary.
                  </p>
                </article>
              </section>

              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-6">
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">Possible readiness results</p>
                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  {readinessResults.map(([title, body]) => (
                    <article key={title} className="rounded-lg border border-white/10 bg-slate-950/40 p-4">
                      <h3 className="font-bold text-white">{title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-slate-300">{body}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section className="grid gap-5 lg:grid-cols-2">
                <article className="rounded-xl border border-cyan-300/15 bg-slate-900/45 p-6">
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">What you receive</p>
                  <ul className="mt-4 space-y-2 text-sm leading-relaxed text-slate-300">
                    {customerReceives.map((item) => (
                      <li key={item} className="flex gap-2"><span className="text-cyan-300">•</span><span>{item}</span></li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-xl border border-white/10 bg-white/[0.025] p-6">
                  <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">Clear limitations</p>
                  <ul className="mt-4 grid gap-2 text-sm leading-relaxed text-slate-300 sm:grid-cols-2">
                    {preflightLimits.map((item) => (
                      <li key={item} className="rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2">{item}</li>
                    ))}
                  </ul>
                </article>
              </section>

              <section className="rounded-xl border border-cyan-300/20 bg-gradient-to-br from-cyan-400/[0.08] to-blue-950/25 p-6">
                <p className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">After the scan</p>
                <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
                  <div>
                    <h2 className="mt-3 text-2xl font-bold text-white">Preflight helps choose the next step.</h2>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">
                      A paid website scan goes deeper: it can crawl more pages, preserve project evidence, compile audit
                      reports, prioritize findings, and connect recommendations to ORB readiness. Public Preflight is the
                      first public fit check, not the full review.
                    </p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                    <a href="/signup?intent=site_review" className="rounded-lg bg-cyan-300 px-5 py-3 text-center text-sm font-bold text-slate-950 transition hover:bg-cyan-200">Proceed to Site Review</a>
                    <a href="/signup?intent=site_update" className="rounded-lg border border-cyan-200/30 px-5 py-3 text-center text-sm font-bold text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10">Request a Site Update</a>
                    <a href="/marketplace" className="rounded-lg border border-cyan-200/30 px-5 py-3 text-center text-sm font-bold text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10">Explore ORB Packages</a>
                    <a href="/signup" className="rounded-lg border border-white/15 px-5 py-3 text-center text-sm font-bold text-slate-200 transition hover:bg-white/10">Create an Account</a>
                  </div>
                </div>
              </section>
            </section>
          )}
        </section>
      </div>
    </main>
  );
};

export default PublicPreflight;
