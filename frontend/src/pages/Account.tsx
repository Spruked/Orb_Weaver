import React from 'react';
import { Customer } from '../services/api';

interface AccountProps {
  customer: Customer;
  onLogout: () => void;
}

const Account: React.FC<AccountProps> = ({ customer, onLogout }) => (
  <div className="space-y-6">
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Account</h1>
      <p className="text-gray-500 mt-1">Customer record and access status</p>
    </div>

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

export default Account;
