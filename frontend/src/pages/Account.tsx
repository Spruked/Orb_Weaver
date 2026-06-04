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

    <div className="card max-w-2xl">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-500">Business</p>
          <p className="font-semibold text-gray-900">{customer.business_name}</p>
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
          <p className="text-sm text-gray-500">Status</p>
          <p className="font-semibold text-gray-900 capitalize">{customer.status}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Created</p>
          <p className="font-semibold text-gray-900">
            {customer.created_at ? new Date(customer.created_at).toLocaleDateString() : '-'}
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
