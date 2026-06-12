import React, { useState } from 'react';
import { api, authStore, Customer } from '../services/api';

const bannerLogo = '/orbweaver1600.png';

interface AuthPageProps {
  onAuthenticated: (customer: Customer) => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [legal, setLegal] = useState({
    terms: false,
    privacy: false,
  });
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    business_name: '',
    company_name: '',
    contact_name: '',
    phone: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'US',
    business_phone: '',
    business_address_line1: '',
    business_address_line2: '',
    business_city: '',
    business_state: '',
    business_postal_code: '',
    business_country: 'US',
    tax_id: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async () => {
    setError('');
    setIsSubmitting(true);
    try {
      const response =
        mode === 'signup'
          ? await api.signup({
              email: form.email,
              password: form.password,
              full_name: form.full_name,
              business_name: form.business_name || null,
              company_name: form.company_name || null,
              contact_name: form.contact_name || null,
              phone: form.phone || null,
              address_line1: form.address_line1,
              address_line2: form.address_line2 || null,
              city: form.city,
              state: form.state,
              postal_code: form.postal_code,
              country: form.country,
              business_phone: form.business_phone || null,
              business_address_line1: form.business_address_line1 || null,
              business_address_line2: form.business_address_line2 || null,
              business_city: form.business_city || null,
              business_state: form.business_state || null,
              business_postal_code: form.business_postal_code || null,
              business_country: form.business_country || null,
              tax_id: form.tax_id || null,
            })
          : await api.login({ email: form.email, password: form.password });
      authStore.setToken(response.token);
      onAuthenticated(response.customer);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isSignup = mode === 'signup';
  const inputClass =
    'w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 shadow-sm focus:border-[#18CFE3] focus:outline-none focus:ring-2 focus:ring-[#18CFE3]/25';
  const linkClass = 'font-semibold text-[#0E7490] hover:text-[#075985]';
  const primaryDisabled =
    isSubmitting ||
    !legal.terms ||
    !legal.privacy ||
    !form.email.trim() ||
    !form.password.trim() ||
    (isSignup &&
      (!form.full_name.trim() ||
        !form.phone.trim() ||
        !form.address_line1.trim() ||
        !form.city.trim() ||
        !form.state.trim() ||
        !form.postal_code.trim() ||
        !form.country.trim()));

  return (
    <div className="min-h-screen bg-[#F2FBFD] px-4 py-4 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col pt-2">
        <header className="mx-auto mb-4 w-full max-w-4xl text-center">
          <img
            src={bannerLogo}
            alt="Orb Weaver"
            className="mx-auto h-48 max-h-[32vh] w-full object-contain sm:h-56"
          />
        </header>

        <main className="rounded-lg border border-slate-200 bg-white p-6 shadow-lg shadow-slate-900/8 sm:p-8">
          <section className="mx-auto max-w-2xl">
            <div className="mb-6 text-center">
              <h2 className="text-2xl font-bold text-slate-950">{isSignup ? 'Create Account' : 'Customer Login'}</h2>
              <p className="mt-1 text-sm text-slate-600">
                {isSignup ? 'Create your Orb Weaver workspace' : 'Access your Orb Weaver workspace'}
              </p>
            </div>

            <div className="mb-6 grid grid-cols-2 gap-2 rounded-md border border-slate-200 bg-slate-50 p-1">
              <button
                onClick={() => setMode('login')}
                className={`rounded-md py-2.5 text-sm font-bold transition ${
                  !isSignup ? 'bg-[#18CFE3] text-[#061A33] shadow-sm' : 'text-slate-700 hover:bg-white'
                }`}
              >
                Login
              </button>
              <button
                onClick={() => setMode('signup')}
                className={`rounded-md py-2.5 text-sm font-bold transition ${
                  isSignup ? 'bg-[#18CFE3] text-[#061A33] shadow-sm' : 'text-slate-700 hover:bg-white'
                }`}
              >
                Create Account
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {isSignup && (
                <>
                  <input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} className={inputClass} placeholder="Full name" />
                  <input value={form.business_name} onChange={(event) => setForm({ ...form, business_name: event.target.value })} className={inputClass} placeholder="Business name" />
                  <input value={form.company_name} onChange={(event) => setForm({ ...form, company_name: event.target.value })} className={inputClass} placeholder="Company name" />
                  <input value={form.contact_name} onChange={(event) => setForm({ ...form, contact_name: event.target.value })} className={inputClass} placeholder="Contact name" />
                  <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className={inputClass} placeholder="Phone" />
                  <input value={form.address_line1} onChange={(event) => setForm({ ...form, address_line1: event.target.value })} className={inputClass} placeholder="Address line 1" />
                  <input value={form.address_line2} onChange={(event) => setForm({ ...form, address_line2: event.target.value })} className={inputClass} placeholder="Address line 2" />
                  <input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} className={inputClass} placeholder="City" />
                  <input value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value })} className={inputClass} placeholder="State" />
                  <input value={form.postal_code} onChange={(event) => setForm({ ...form, postal_code: event.target.value })} className={inputClass} placeholder="Postal code" />
                  <input value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })} className={inputClass} placeholder="Country" />
                  <input value={form.business_phone} onChange={(event) => setForm({ ...form, business_phone: event.target.value })} className={inputClass} placeholder="Business phone" />
                  <input value={form.business_address_line1} onChange={(event) => setForm({ ...form, business_address_line1: event.target.value })} className={inputClass} placeholder="Business address line 1" />
                  <input value={form.business_address_line2} onChange={(event) => setForm({ ...form, business_address_line2: event.target.value })} className={inputClass} placeholder="Business address line 2" />
                  <input value={form.business_city} onChange={(event) => setForm({ ...form, business_city: event.target.value })} className={inputClass} placeholder="Business city" />
                  <input value={form.business_state} onChange={(event) => setForm({ ...form, business_state: event.target.value })} className={inputClass} placeholder="Business state" />
                  <input value={form.business_postal_code} onChange={(event) => setForm({ ...form, business_postal_code: event.target.value })} className={inputClass} placeholder="Business postal code" />
                  <input value={form.business_country} onChange={(event) => setForm({ ...form, business_country: event.target.value })} className={inputClass} placeholder="Business country" />
                  <input value={form.tax_id} onChange={(event) => setForm({ ...form, tax_id: event.target.value })} className={inputClass} placeholder="Business tax ID" />
                </>
              )}
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                className={inputClass}
                placeholder="Email address"
              />
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                className={inputClass}
                placeholder="Password"
              />
            </div>

            <div className="mt-5 space-y-2 text-sm text-slate-700">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={legal.terms}
                  onChange={(event) => setLegal({ ...legal, terms: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-[#18CFE3] focus:ring-[#18CFE3]"
                />
                <span>
                  I agree to the{' '}
                  <a href="/terms" className={linkClass}>
                    Terms of Service
                  </a>
                  .
                </span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={legal.privacy}
                  onChange={(event) => setLegal({ ...legal, privacy: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-[#18CFE3] focus:ring-[#18CFE3]"
                />
                <span>
                  I agree to the{' '}
                  <a href="/privacy" className={linkClass}>
                    Privacy Policy
                  </a>
                  .
                </span>
              </label>
            </div>

            {error && <div className="mt-4 text-sm font-medium text-red-600">{error}</div>}

            <button
              onClick={submit}
              disabled={primaryDisabled}
              className="mt-6 w-full rounded-md bg-[#18CFE3] py-3 text-sm font-bold text-[#061A33] shadow-sm transition hover:bg-[#0E7490] hover:text-white disabled:cursor-not-allowed disabled:bg-[#18CFE3]/60 disabled:text-[#061A33]/70"
            >
              {isSubmitting ? 'Working...' : isSignup ? 'Create Account' : 'Login'}
            </button>
          </section>

          <section className="mx-auto mt-8 grid max-w-4xl gap-4 border-t border-slate-200 pt-7 md:grid-cols-2">
            <article className="rounded-md border border-slate-200 bg-[#fbfcfc] p-5">
              <h3 className="text-lg font-bold text-slate-950">What Orb Weaver Audits</h3>
              <div className="mt-3 space-y-3 text-sm leading-6 text-slate-700">
                <p>Technical crawl status, page inventory, redirects, SSL, sitemap, robots, schema, internal links, and crawl coverage.</p>
                <p>SEO, performance, accessibility, content depth, mobile readiness, and security audit signals.</p>
                <p>Customer projects, report compiler files, checkout orders, and deterministic client intelligence packs.</p>
              </div>
            </article>
            <article className="rounded-md border border-slate-200 bg-[#fbfcfc] p-5">
              <h3 className="text-lg font-bold text-slate-950">Built for Operators</h3>
              <div className="mt-3 space-y-3 text-sm leading-6 text-slate-700">
                <p>
                  Customer records, carts, crawl jobs, reports, and client packs stay in the Orb Weaver backend
                  database while crawls remain local-first and deterministic.
                </p>
                <p>Every report should explain what was found, why it matters, and what action should happen next.</p>
              </div>
            </article>
          </section>

          <footer className="mx-auto mt-7 max-w-4xl border-t border-slate-200 pt-5 text-center text-xs leading-6 text-slate-500">
            <p>
              Pro Prime Series Orb Weaver. Copyright and proprietary notices apply to all software, workflows, branding,
              reports, data structures, and generated materials in this system.
            </p>
            <nav className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-2">
              <a className={linkClass} href="/sitemap.xml">Site Map</a>
              <a className={linkClass} href="/privacy">Privacy Policy</a>
              <a className={linkClass} href="/terms">Terms</a>
              <a className={linkClass} href="https://spruked.com">spruked.com</a>
              <a className={linkClass} href="https://truemarkmint.com">truemarkmint.com</a>
              <a className={linkClass} href="https://certsig.com">certsig.com</a>
              <a className={linkClass} href="https://alphacertsig.com">alphacertsig.com</a>
            </nav>
          </footer>
        </main>
      </div>
    </div>
  );
};

export default AuthPage;
