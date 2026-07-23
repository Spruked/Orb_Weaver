import React, { useEffect, useState } from 'react';
import { AdminCustomer, CaliCrmContact, api } from '../services/api';

const AdminCustomers: React.FC = () => {
  const [customers, setCustomers] = useState<AdminCustomer[]>([]);
  const [crmContacts, setCrmContacts] = useState<CaliCrmContact[]>([]);
  const [crmRoot, setCrmRoot] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isExportingCrm, setIsExportingCrm] = useState(false);
  const [isCreatingCrmContact, setIsCreatingCrmContact] = useState(false);
  const [newCrmContact, setNewCrmContact] = useState({
    display_name: '',
    company_name: '',
    role_title: '',
    email: '',
    phone: '',
    website: '',
    tags: '',
    notes: '',
  });
  const [crmExportResult, setCrmExportResult] = useState<{
    status: string;
    record_count: number;
    path: string;
    crm_url: string;
  } | null>(null);

  useEffect(() => {
    Promise.all([
      api.adminListCustomers(),
      api.adminListCaliCrmContacts(),
    ])
      .then(([nextCustomers, nextCrm]) => {
        setCustomers(nextCustomers);
        setCrmContacts(nextCrm.contacts);
        setCrmRoot(nextCrm.dossier_root);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Admin data load failed'))
      .finally(() => setIsLoading(false));
  }, []);

  const handleCrmExport = async () => {
    setError('');
    setCrmExportResult(null);
    setIsExportingCrm(true);
    try {
      setCrmExportResult(await api.adminExportCustomersToCaliCrm());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CALI CRM export failed');
    } finally {
      setIsExportingCrm(false);
    }
  };

  const handleCreateCrmContact = async () => {
    if (!newCrmContact.display_name.trim()) return;
    setError('');
    setIsCreatingCrmContact(true);
    try {
      const created = await api.adminCreateCaliCrmContact({
        display_name: newCrmContact.display_name.trim(),
        contact_type: 'business_contact',
        company_name: newCrmContact.company_name.trim() || null,
        role_title: newCrmContact.role_title.trim() || null,
        email: newCrmContact.email.trim() || null,
        phone: newCrmContact.phone.trim() || null,
        website: newCrmContact.website.trim() || null,
        relationship_status: 'active',
        tags: newCrmContact.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
        notes: newCrmContact.notes,
      });
      setCrmContacts((current) => [created.contact, ...current]);
      setCrmRoot((current) => current || created.dossier.path.split('/contacts/')[0] + '/contacts');
      setNewCrmContact({ display_name: '', company_name: '', role_title: '', email: '', phone: '', website: '', tags: '', notes: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CALI CRM contact creation failed');
    } finally {
      setIsCreatingCrmContact(false);
    }
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading customers...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backend Admin</h1>
          <p className="text-gray-500 mt-1">Customer records stay separate from the manual CALI CRM contact database</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <a
            href="http://localhost:21010/"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Open local CALI CRM
          </a>
          <a
            href="http://localhost:19000"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Open Prime Mail
          </a>
          <button
            onClick={handleCrmExport}
            disabled={isExportingCrm}
            className="inline-flex items-center justify-center rounded-lg bg-brand-dark px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isExportingCrm ? 'Exporting customers...' : 'Export customers to CALI CRM'}
          </button>
        </div>
      </div>

      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <section className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <article className="card">
          <h2 className="text-lg font-bold text-gray-900">CALI CRM dossier support</h2>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            The CALI CRM contact database is separate from Orb Weaver customers. Add business contacts here when you
            want dossier folders for owner-added documents, research notes, web history, relationship knowledge,
            follow-ups, and source provenance.
          </p>
          <a
            href="http://localhost:21010/"
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center justify-center rounded-lg bg-brand-orange px-4 py-2 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white"
          >
            Launch CRM workspace
          </a>
          <a
            href="http://localhost:19000"
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Open Prime Mail
          </a>
        </article>
        <article className="card bg-slate-50">
          <h2 className="text-lg font-bold text-gray-900">Available dossier areas</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {['Documents', 'Research', 'Web history', 'Knowledge', 'Follow-ups', 'Source log'].map((label) => (
              <span key={label} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700">{label}</span>
            ))}
          </div>
        </article>
      </section>

      {crmExportResult && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Exported {crmExportResult.record_count} customer records to the CALI CRM import queue.
          <div className="mt-1 break-all text-xs">
            Import: {crmExportResult.path}
          </div>
        </div>
      )}

      <section className="card">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Manual CRM contacts</h2>
            <p className="mt-1 text-sm text-gray-500">Dossier root: {crmRoot || 'Created when the first contact is added'}</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700">{crmContacts.length} contacts</span>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-4">
          <input value={newCrmContact.display_name} onChange={(event) => setNewCrmContact((current) => ({ ...current, display_name: event.target.value }))} placeholder="Contact name" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.company_name} onChange={(event) => setNewCrmContact((current) => ({ ...current, company_name: event.target.value }))} placeholder="Company" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.role_title} onChange={(event) => setNewCrmContact((current) => ({ ...current, role_title: event.target.value }))} placeholder="Role/title" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.email} onChange={(event) => setNewCrmContact((current) => ({ ...current, email: event.target.value }))} placeholder="Email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.phone} onChange={(event) => setNewCrmContact((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.website} onChange={(event) => setNewCrmContact((current) => ({ ...current, website: event.target.value }))} placeholder="Website" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <input value={newCrmContact.tags} onChange={(event) => setNewCrmContact((current) => ({ ...current, tags: event.target.value }))} placeholder="Tags, comma-separated" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <button onClick={handleCreateCrmContact} disabled={isCreatingCrmContact || !newCrmContact.display_name.trim()} className="rounded-lg bg-brand-orange px-4 py-2 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50">
            {isCreatingCrmContact ? 'Creating...' : 'Create dossier'}
          </button>
        </div>
        <textarea value={newCrmContact.notes} onChange={(event) => setNewCrmContact((current) => ({ ...current, notes: event.target.value }))} placeholder="Opening notes" rows={3} className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

        <div className="mt-5 divide-y divide-gray-100">
          {crmContacts.length === 0 ? (
            <p className="text-sm text-gray-500">No manual CRM contacts yet.</p>
          ) : crmContacts.slice(0, 10).map((contact) => (
            <div key={contact.id} className="py-3 first:pt-0 last:pb-0">
              <p className="font-semibold text-gray-900">{contact.display_name}</p>
              <p className="text-sm text-gray-500">{[contact.company_name, contact.role_title, contact.email].filter(Boolean).join(' · ') || contact.contact_type}</p>
              {contact.dossier_path && <p className="mt-1 break-all text-xs text-gray-400">{contact.dossier_path}</p>}
            </div>
          ))}
        </div>
      </section>

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
