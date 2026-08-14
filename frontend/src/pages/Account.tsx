import React, { useEffect, useState } from 'react';
import { api, AccountWorkspaceSummary, Customer } from '../services/api';

interface AccountProps {
  customer: Customer;
  onLogout: () => void;
}

const Account: React.FC<AccountProps> = ({ customer, onLogout }) => {
  const [workspace, setWorkspace] = useState<AccountWorkspaceSummary | null>(null);
  const [workspaceError, setWorkspaceError] = useState('');

  useEffect(() => {
    let stopped = false;
    const loadWorkspace = async () => {
      try {
        const summary = await api.getAccountWorkspaceSummary();
        if (!stopped) setWorkspace(summary);
      } catch (err) {
        if (!stopped) setWorkspaceError(err instanceof Error ? err.message : 'Unable to load workspace scan status');
      }
    };
    void loadWorkspace();
    return () => { stopped = true; };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Account</h1>
        <p className="text-gray-500 mt-1">Customer record, workspace status, and latest scan differences</p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <p className="text-sm text-gray-500">Latest workspace</p>
          <p className="mt-1 font-bold text-gray-900">{workspace?.project?.name || 'No workspace yet'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.project?.domain || '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Latest crawl</p>
          <p className="mt-1 font-bold capitalize text-gray-900">{workspace?.latest_crawl?.status || 'Not started'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.latest_crawl ? `${workspace.latest_crawl.pages_crawled || 0} pages processed` : '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Latest audit</p>
          <p className="mt-1 font-bold text-gray-900">{workspace?.latest_audit?.score != null ? `${workspace.latest_audit.score}/100` : 'Not run'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.latest_audit?.created_at ? new Date(workspace.latest_audit.created_at).toLocaleString() : '-'}</p>
        </div>
      </section>
      {workspaceError && <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">{workspaceError}</div>}

    <div className="card max-w-4xl">
      <div className="mb-6 border-b border-gray-100 pb-5">
        <p className="text-sm text-gray-500">Business Account</p>
        <h2 className="text-2xl font-bold text-gray-900 mt-1">{customer.business_name}</h2>
        <p className="text-sm text-gray-600 mt-1">{customer.email}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-500">Customer ID</p>
          <p className="font-semibold text-gray-900">{customer.id}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Full Name</p>
          <p className="font-semibold text-gray-900">{customer.full_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business</p>
          <p className="font-semibold text-gray-900">{customer.business_name}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Company</p>
          <p className="font-semibold text-gray-900">{customer.company_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Email</p>
          <p className="font-semibold text-gray-900">{customer.email}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Contact</p>
          <p className="font-semibold text-gray-900">{customer.contact_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Phone</p>
          <p className="font-semibold text-gray-900">{customer.phone || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Address</p>
          <p className="font-semibold text-gray-900">
            {[customer.address_line1, customer.address_line2, customer.city, customer.state, customer.postal_code, customer.country]
              .filter(Boolean)
              .join(', ') || '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business Phone</p>
          <p className="font-semibold text-gray-900">{customer.business_phone || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business Address</p>
          <p className="font-semibold text-gray-900">
            {[
              customer.business_address_line1,
              customer.business_address_line2,
              customer.business_city,
              customer.business_state,
              customer.business_postal_code,
              customer.business_country,
            ]
              .filter(Boolean)
              .join(', ') || '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Tax ID</p>
          <p className="font-semibold text-gray-900">{customer.tax_id || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Admin</p>
          <p className="font-semibold text-gray-900">{customer.is_admin ? 'Yes' : 'No'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Status</p>
          <p className="font-semibold text-gray-900 capitalize">{customer.status}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Created</p>
          <p className="font-semibold text-gray-900">
            {customer.created_at ? new Date(customer.created_at).toLocaleString() : '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Updated</p>
          <p className="font-semibold text-gray-900">
            {customer.updated_at ? new Date(customer.updated_at).toLocaleString() : '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Last Login</p>
          <p className="font-semibold text-gray-900">
            {customer.last_login_at ? new Date(customer.last_login_at).toLocaleString() : '-'}
          </p>
        </div>
      </div>

      <button onClick={onLogout} className="mt-8 btn-secondary">
        Logout
      </button>
    </div>
  </div>
  );
};

export default Account;
