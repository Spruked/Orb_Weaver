import React, { useEffect, useState } from 'react';
import { AdminCustomer, api } from '../services/api';

const AdminCustomers: React.FC = () => {
  const [customers, setCustomers] = useState<AdminCustomer[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .adminListCustomers()
      .then(setCustomers)
      .catch((err) => setError(err instanceof Error ? err.message : 'Admin customer load failed'))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <div className="text-gray-500">Loading customers...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Backend Admin</h1>
        <p className="text-gray-500 mt-1">Customer records, profile fields, projects, carts, and checkout activity</p>
      </div>

      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="py-2">Customer</th>
              <th>Company</th>
              <th>Contact</th>
              <th>Address</th>
              <th>Projects</th>
              <th>Cart</th>
              <th>Orders</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((customer) => (
              <tr key={customer.id} className="border-b last:border-0 align-top">
                <td className="py-3">
                  <p className="font-semibold text-gray-900">{customer.full_name || customer.business_name}</p>
                  <p className="text-gray-500">{customer.email}</p>
                </td>
                <td className="py-3">{customer.company_name || customer.business_name || '-'}</td>
                <td className="py-3">
                  <p>{customer.phone || '-'}</p>
                  <p className="text-gray-500">{customer.business_phone || ''}</p>
                </td>
                <td className="py-3 max-w-xs">
                  {[customer.address_line1, customer.city, customer.state, customer.postal_code, customer.country].filter(Boolean).join(', ') || '-'}
                </td>
                <td className="py-3">{customer.project_count}</td>
                <td className="py-3">{customer.cart_item_count}</td>
                <td className="py-3">{customer.checkout_order_count}</td>
                <td className="py-3">{customer.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminCustomers;
