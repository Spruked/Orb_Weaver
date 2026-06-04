import React, { useState } from 'react';
import { Lock, UserPlus } from 'lucide-react';
import { api, authStore, Customer } from '../services/api';

interface AuthPageProps {
  onAuthenticated: (customer: Customer) => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [form, setForm] = useState({
    email: '',
    password: '',
    business_name: '',
    contact_name: '',
    phone: ''
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
              business_name: form.business_name,
              contact_name: form.contact_name || null,
              phone: form.phone || null
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

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-6">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-lg shadow-sm p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-lg bg-brand-orange/10 flex items-center justify-center">
            {isSignup ? <UserPlus className="w-6 h-6 text-brand-orange" /> : <Lock className="w-6 h-6 text-brand-orange" />}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Orb Weaver</h1>
            <p className="text-sm text-gray-500">{isSignup ? 'Create customer access' : 'Customer login'}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-6">
          <button
            onClick={() => setMode('login')}
            className={`py-2 rounded-lg font-medium ${!isSignup ? 'bg-brand-orange text-white' : 'bg-gray-100 text-gray-700'}`}
          >
            Login
          </button>
          <button
            onClick={() => setMode('signup')}
            className={`py-2 rounded-lg font-medium ${isSignup ? 'bg-brand-orange text-white' : 'bg-gray-100 text-gray-700'}`}
          >
            Signup
          </button>
        </div>

        <div className="space-y-4">
          {isSignup && (
            <>
              <input
                value={form.business_name}
                onChange={(event) => setForm({ ...form, business_name: event.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                placeholder="Business name"
              />
              <input
                value={form.contact_name}
                onChange={(event) => setForm({ ...form, contact_name: event.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                placeholder="Contact name"
              />
              <input
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                placeholder="Phone"
              />
            </>
          )}
          <input
            type="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
            placeholder="Email"
          />
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
            placeholder="Password"
          />
        </div>

        {error && <div className="mt-4 text-sm text-red-600">{error}</div>}

        <button
          onClick={submit}
          disabled={isSubmitting || !form.email.trim() || !form.password.trim() || (isSignup && !form.business_name.trim())}
          className="mt-6 w-full py-3 bg-brand-orange text-white rounded-lg font-semibold hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Working...' : isSignup ? 'Create Account' : 'Login'}
        </button>
      </div>
    </div>
  );
};

export default AuthPage;
