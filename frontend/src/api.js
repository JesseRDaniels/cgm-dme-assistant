const API_BASE = 'http://localhost:8001';

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
