async function request(path, options) {
  const res = await fetch(`/api${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* corps non JSON */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? null : res.json();
}

const post = (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) });

export const api = {
  health: () => request('/health'),
  nodes: () => request('/nodes'),
  generate: (prompt) => post('/generate', { prompt }),
  validate: (workflow) => post('/validate', workflow),
  run: (workflow, { dryRun, approved, workflowId }) =>
    post('/run', { workflow, dry_run: dryRun, approved: approved ?? false, workflow_id: workflowId ?? null }),
  runs: (workflowId) => request(`/runs${workflowId ? `?workflow_id=${workflowId}` : ''}`),
  workflows: () => request('/workflows'),
  saveWorkflow: (workflow, id) =>
    id ? request(`/workflows/${id}`, { method: 'PUT', body: JSON.stringify(workflow) }) : post('/workflows', workflow),
  deleteWorkflow: (id) => request(`/workflows/${id}`, { method: 'DELETE' }),
  // Module ERP (docs/erp-contract.md)
  customers: () => request('/erp/customers'),
  createCustomer: (customer) => post('/erp/customers', customer),
  products: () => request('/erp/products'),
  sales: () => request('/erp/sales'),
  createSale: ({ customerId, items, sendInvoice = true }) =>
    post('/erp/sales', { customer_id: customerId, items, send_invoice: sendInvoice }),
  invoiceUrl: (id) => `/api/erp/sales/${id}/invoice`,
  automation: () => request('/erp/automation'),
  installAutomation: () => post('/erp/automation/install', {}),
  // Générateur d'applications (docs/app-builder-contract.md)
  apps: () => request('/apps'),
  buildApps: (prompt) => post('/apps/build', { prompt }),
  appBuilds: () => request('/apps/builds'),
  resetApps: () => post('/apps/reset', {}),
};
