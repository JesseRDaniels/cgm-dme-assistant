const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export async function chat(query, context = null) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, context }),
  });
  if (!response.ok) throw new Error('Chat request failed');
  return response.json();
}

export async function lookupCode(code) {
  const response = await fetch(`${API_BASE}/api/codes/${code}`);
  if (!response.ok) throw new Error('Code not found');
  return response.json();
}

export async function searchCodes(query) {
  const response = await fetch(`${API_BASE}/api/codes?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error('Search failed');
  return response.json();
}

export async function generateDWO(data) {
  const response = await fetch(`${API_BASE}/api/generate/dwo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('DWO generation failed');
  return response.json();
}

export async function generatePriorAuth(data) {
  const response = await fetch(`${API_BASE}/api/generate/prior-auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Prior auth generation failed');
  return response.json();
}

export async function generateAppeal(data) {
  const response = await fetch(`${API_BASE}/api/generate/appeal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Appeal generation failed');
  return response.json();
}

export async function uploadBatch(file, processingType) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/batch/upload?processing_type=${processingType}`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Upload failed');
  return response.json();
}

export async function getBatchStatus(batchId) {
  const response = await fetch(`${API_BASE}/api/batch/${batchId}/status`);
  if (!response.ok) throw new Error('Status check failed');
  return response.json();
}

export async function getBatchResults(batchId) {
  const response = await fetch(`${API_BASE}/api/batch/${batchId}/results`);
  if (!response.ok) throw new Error('Results fetch failed');
  return response.json();
}

export async function auditClaim(data) {
  const response = await fetch(`${API_BASE}/api/audit/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Audit failed');
  return response.json();
}

export async function quickAudit(data) {
  const response = await fetch(`${API_BASE}/api/audit/quick`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Audit failed');
  return response.json();
}

// Policy endpoints
export async function getPolicy(policyId, includeCriteria = true, includeCodes = true) {
  const params = new URLSearchParams({
    include_criteria: includeCriteria,
    include_codes: includeCodes,
  });
  const response = await fetch(`${API_BASE}/api/policies/${policyId}?${params}`);
  if (!response.ok) throw new Error('Policy not found');
  return response.json();
}

export async function comparePolicies(codes, jurisdictions = null) {
  const params = new URLSearchParams({ codes: codes.join(',') });
  if (jurisdictions) params.append('jurisdictions', jurisdictions.join(','));
  const response = await fetch(`${API_BASE}/api/policies/compare/jurisdictions?${params}`);
  if (!response.ok) throw new Error('Comparison failed');
  return response.json();
}

export async function getPolicyChanges(since = null, policyId = null, changeType = null, limit = 20) {
  const params = new URLSearchParams({ limit });
  if (since) params.append('since', since);
  if (policyId) params.append('policy_id', policyId);
  if (changeType) params.append('change_type', changeType);
  const response = await fetch(`${API_BASE}/api/policies/changes/recent?${params}`);
  if (!response.ok) throw new Error('Failed to fetch changes');
  return response.json();
}
