import React, { useEffect } from 'react';
import PublicHeader from '../components/PublicHeader';
import './PublicLeadPage.css';

type PublicLeadPageProps = {
  type: 'beta' | 'investor';
};

const FORM_ENDPOINT = 'https://formsubmit.co/bryanspruk7@outlook.com';

const PublicLeadPage: React.FC<PublicLeadPageProps> = ({ type }) => {
  const isBeta = type === 'beta';
  const submitted = new URLSearchParams(window.location.search).get('submitted') === '1';
  const pageUrl = isBeta
    ? 'https://orbweaver.spruked.com/founding-beta?submitted=1'
    : 'https://orbweaver.spruked.com/investor-contact?submitted=1';

  useEffect(() => {
    document.title = isBeta
      ? 'Join the Founding Beta | ORB Weaver'
      : 'Private Investor Discussion | ORB Weaver';
  }, [isBeta]);

  return (
    <main className="ow-lead-page">
      <div className="ow-lead-grid" aria-hidden="true" />
      <div className="ow-lead-glow" aria-hidden="true" />
      <PublicHeader theme="dark" />

      <section className="ow-lead-shell">
        <div className="ow-lead-intro">
          <p className="ow-lead-kicker">
            {isBeta ? 'FOUNDING BETA PROGRAM' : 'PRIVATE INVESTOR BRIEFING'}
          </p>
          <h1>
            {isBeta ? (
              <>
                Help shape the first <span>deployable Website ORB.</span>
              </>
            ) : (
              <>
                Start a serious discussion about <span>ORB Weaver.</span>
              </>
            )}
          </h1>
          <p className="ow-lead-summary">
            {isBeta
              ? 'We are selecting a limited group of website owners and operators to test the real ORB deployment, report friction, and help prove measurable visitor value.'
              : 'This page is for private investors, strategic partners, agencies, and technical partners who want a direct conversation about the product, market, deployment model, and funding path.'}
          </p>

          <div className="ow-lead-principles">
            {isBeta ? (
              <>
                <article>
                  <strong>Real websites</strong>
                  <span>Testing happens against actual visitor paths, content, forms, and business goals.</span>
                </article>
                <article>
                  <strong>Direct founder access</strong>
                  <span>Founding testers provide feedback close to the product decisions.</span>
                </article>
                <article>
                  <strong>Limited enrollment</strong>
                  <span>Applications are reviewed for fit; submitting does not guarantee acceptance.</span>
                </article>
              </>
            ) : (
              <>
                <article>
                  <strong>Product proof</strong>
                  <span>Review the working Website ORB, present architecture, and deployment direction.</span>
                </article>
                <article>
                  <strong>Commercial case</strong>
                  <span>Discuss target markets, recurring deployment value, and distribution strategy.</span>
                </article>
                <article>
                  <strong>Private follow-up</strong>
                  <span>Sensitive materials are shared only after the initial conversation and qualification.</span>
                </article>
              </>
            )}
          </div>

          <a className="ow-lead-back" href="/">
            Return to the ORB Weaver product site
          </a>
        </div>

        <section className="ow-lead-card" aria-labelledby="lead-form-title">
          {submitted ? (
            <div className="ow-lead-success" role="status">
              <div className="ow-lead-success-mark">✓</div>
              <p className="ow-lead-kicker">RECEIVED</p>
              <h2 id="lead-form-title">Your message is in the queue.</h2>
              <p>
                {isBeta
                  ? 'Thank you for applying to the Founding Beta. Your website and goals will be reviewed before the next step is offered.'
                  : 'Thank you for reaching out. Your information will be reviewed before a private discussion is scheduled.'}
              </p>
              <a className="ow-lead-submit" href="/">
                Return to ORB Weaver
              </a>
            </div>
          ) : (
            <>
              <div className="ow-lead-card-heading">
                <p className="ow-lead-kicker">{isBeta ? 'APPLY FOR REVIEW' : 'REQUEST A DISCUSSION'}</p>
                <h2 id="lead-form-title">{isBeta ? 'Founding Beta application' : 'Private contact request'}</h2>
                <p>Fields marked with an asterisk are required.</p>
              </div>

              <form className="ow-lead-form" action={FORM_ENDPOINT} method="POST">
                <input type="hidden" name="_subject" value={isBeta ? 'ORB Weaver Founding Beta Application' : 'ORB Weaver Private Investor Discussion Request'} />
                <input type="hidden" name="_next" value={pageUrl} />
                <input type="hidden" name="_template" value="table" />
                <input type="hidden" name="_captcha" value="false" />
                <input type="hidden" name="form_type" value={isBeta ? 'founding_beta' : 'private_investor_discussion'} />
                <input className="ow-lead-honey" type="text" name="_honey" tabIndex={-1} autoComplete="off" />

                <div className="ow-lead-row">
                  <label>
                    Full name *
                    <input name="full_name" type="text" required maxLength={120} autoComplete="name" />
                  </label>
                  <label>
                    Email address *
                    <input name="email" type="email" required maxLength={180} autoComplete="email" />
                  </label>
                </div>

                <div className="ow-lead-row">
                  <label>
                    {isBeta ? 'Business or organization' : 'Organization or fund'}
                    <input name="organization" type="text" maxLength={180} autoComplete="organization" />
                  </label>
                  <label>
                    {isBeta ? 'Your role' : 'Title or role'}
                    <input name="role" type="text" maxLength={140} autoComplete="organization-title" />
                  </label>
                </div>

                {isBeta ? (
                  <>
                    <label>
                      Website URL *
                      <input name="website_url" type="url" required placeholder="https://" maxLength={300} />
                    </label>
                    <div className="ow-lead-row">
                      <label>
                        Website platform
                        <select name="website_platform" defaultValue="">
                          <option value="" disabled>Select one</option>
                          <option>WordPress</option>
                          <option>Shopify</option>
                          <option>Wix</option>
                          <option>Squarespace</option>
                          <option>React / Next.js</option>
                          <option>Custom HTML or application</option>
                          <option>Other or unsure</option>
                        </select>
                      </label>
                      <label>
                        Primary visitor goal
                        <select name="primary_visitor_goal" defaultValue="">
                          <option value="" disabled>Select one</option>
                          <option>Generate qualified leads</option>
                          <option>Sell products</option>
                          <option>Book appointments</option>
                          <option>Explain complex services</option>
                          <option>Customer support</option>
                          <option>Guide users through a portal</option>
                          <option>Other</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      What should the ORB help visitors accomplish? *
                      <textarea name="orb_goal" required rows={5} maxLength={1800} />
                    </label>
                    <label>
                      What can you commit to during beta testing?
                      <textarea name="testing_commitment" rows={4} maxLength={1200} placeholder="Examples: weekly feedback, visitor testing, conversion review, bug reports." />
                    </label>
                  </>
                ) : (
                  <>
                    <div className="ow-lead-row">
                      <label>
                        Relationship to ORB Weaver *
                        <select name="relationship" required defaultValue="">
                          <option value="" disabled>Select one</option>
                          <option>Private investor</option>
                          <option>Strategic partner</option>
                          <option>Agency or channel partner</option>
                          <option>Technical or platform partner</option>
                          <option>Advisor</option>
                          <option>Other</option>
                        </select>
                      </label>
                      <label>
                        Potential engagement range
                        <select name="engagement_range" defaultValue="">
                          <option value="" disabled>Optional</option>
                          <option>Under $25,000</option>
                          <option>$25,000–$99,999</option>
                          <option>$100,000–$249,999</option>
                          <option>$250,000–$499,999</option>
                          <option>$500,000 or more</option>
                          <option>Strategic partnership, not capital</option>
                          <option>Prefer to discuss privately</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      Primary area of interest *
                      <textarea name="area_of_interest" required rows={4} maxLength={1600} placeholder="Product, market, licensing, distribution, architecture, funding, or strategic fit." />
                    </label>
                    <label>
                      Message *
                      <textarea name="message" required rows={6} maxLength={2400} />
                    </label>
                  </>
                )}

                <label className="ow-lead-consent">
                  <input name="contact_consent" type="checkbox" required value="yes" />
                  <span>I authorize ORB Weaver to contact me about this request. *</span>
                </label>

                <button className="ow-lead-submit" type="submit">
                  {isBeta ? 'Submit Founding Beta Application' : 'Request a Private Discussion'}
                </button>

                <p className="ow-lead-fineprint">
                  Your information is used only to evaluate and respond to this request. Do not submit passwords, account credentials, banking details, or confidential technical material through this form.
                </p>
              </form>
            </>
          )}
        </section>
      </section>
    </main>
  );
};

export default PublicLeadPage;
