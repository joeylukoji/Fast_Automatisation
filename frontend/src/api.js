async function request(path, options) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* corps non JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  nodes: () => request('/nodes'),
  generate: (prompt) => request('/generate', { method: 'POST', body: JSON.stringify({ prompt }) }),
  run: (workflow, { dryRun, approved }) =>
    request('/run', {
      method: 'POST',
      body: JSON.stringify({ workflow, dry_run: dryRun, approved: approved ?? false }),
    }),
};
