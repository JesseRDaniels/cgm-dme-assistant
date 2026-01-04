import { useState } from 'react';
import { getPolicy, comparePolicies, getPolicyChanges } from '../api';

export default function PolicyBrowser() {
  const [activeView, setActiveView] = useState('lookup');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Policy lookup state
  const [policyId, setPolicyId] = useState('');
  const [policy, setPolicy] = useState(null);

  // Compare state
  const [compareCodes, setCompareCodes] = useState('');
  const [comparison, setComparison] = useState(null);

  // Changes state
  const [changes, setChanges] = useState([]);

  const handlePolicyLookup = async (e) => {
    e.preventDefault();
    if (!policyId.trim()) return;

    setLoading(true);
    setError('');
    setPolicy(null);

    try {
      const data = await getPolicy(policyId.trim().toUpperCase());
      setPolicy(data);
    } catch (err) {
      setError('Policy not found');
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!compareCodes.trim()) return;

    setLoading(true);
    setError('');
    setComparison(null);

    try {
      const codes = compareCodes.split(',').map(c => c.trim().toUpperCase());
      const data = await comparePolicies(codes);
      setComparison(data);
    } catch (err) {
      setError('Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const loadChanges = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await getPolicyChanges();
      setChanges(data.changes || []);
    } catch (err) {
      setError('Failed to load changes');
    } finally {
      setLoading(false);
    }
  };

  const quickPolicies = ['L33822', 'L33831', 'A52458'];
  const quickCodes = ['K0553', 'A9276', 'A9277'];

  const views = [
    { id: 'lookup', label: 'Policy Lookup' },
    { id: 'compare', label: 'Compare' },
    { id: 'changes', label: 'Changes' },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Medicare Policy Browser</h2>

      {/* View Toggle */}
      <div className="flex gap-2 mb-6 border-b border-gray-200 pb-4">
        {views.map((view) => (
          <button
            key={view.id}
            onClick={() => {
              setActiveView(view.id);
              setError('');
              if (view.id === 'changes' && changes.length === 0) loadChanges();
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeView === view.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {view.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Policy Lookup View */}
      {activeView === 'lookup' && (
        <div>
          <form onSubmit={handlePolicyLookup} className="mb-6">
            <div className="flex gap-2">
              <input
                type="text"
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
                placeholder="Enter policy ID (e.g., L33822)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {loading ? 'Loading...' : 'Lookup'}
              </button>
            </div>
          </form>

          <div className="mb-6">
            <p className="text-sm text-gray-500 mb-2">Quick lookup:</p>
            <div className="flex flex-wrap gap-2">
              {quickPolicies.map((id) => (
                <button
                  key={id}
                  onClick={() => {
                    setPolicyId(id);
                    getPolicy(id).then(setPolicy).catch(() => setError('Policy not found'));
                  }}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm font-mono transition"
                >
                  {id}
                </button>
              ))}
            </div>
          </div>

          {policy && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold font-mono text-blue-600">{policy.policy_id}</h3>
                  <p className="text-lg text-gray-700">{policy.title}</p>
                </div>
                <div className="flex gap-2">
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                    {policy.policy_type}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded ${
                    policy.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {policy.status}
                  </span>
                </div>
              </div>

              {policy.summary && (
                <p className="text-gray-600 mb-4">{policy.summary}</p>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div>
                  <p className="font-medium text-gray-500">Jurisdiction</p>
                  <p className="text-gray-800">{policy.jurisdiction || 'National'}</p>
                </div>
                <div>
                  <p className="font-medium text-gray-500">MAC</p>
                  <p className="text-gray-800">{policy.mac || 'N/A'}</p>
                </div>
                <div>
                  <p className="font-medium text-gray-500">Effective Date</p>
                  <p className="text-gray-800">{policy.effective_date || 'N/A'}</p>
                </div>
                {policy.source_url && (
                  <div>
                    <p className="font-medium text-gray-500">Source</p>
                    <a href={policy.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      View on CMS
                    </a>
                  </div>
                )}
              </div>

              {/* Coverage Criteria */}
              {policy.criteria && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-700 mb-2">Coverage Criteria</h4>
                  <div className="space-y-3">
                    {policy.criteria.indications && policy.criteria.indications.length > 0 && (
                      <div className="p-3 bg-green-50 border border-green-200 rounded">
                        <p className="font-medium text-green-800 text-sm mb-1">Indications</p>
                        <ul className="text-sm text-green-700 space-y-1">
                          {policy.criteria.indications.map((item, i) => (
                            <li key={i}>• {item.text}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {policy.criteria.documentation && policy.criteria.documentation.length > 0 && (
                      <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                        <p className="font-medium text-blue-800 text-sm mb-1">Documentation Required</p>
                        <ul className="text-sm text-blue-700 space-y-1">
                          {policy.criteria.documentation.map((item, i) => (
                            <li key={i}>• {item.text}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {policy.criteria.limitations && policy.criteria.limitations.length > 0 && (
                      <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="font-medium text-yellow-800 text-sm mb-1">Limitations</p>
                        <ul className="text-sm text-yellow-700 space-y-1">
                          {policy.criteria.limitations.map((item, i) => (
                            <li key={i}>• {item.text}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {policy.criteria.frequency && policy.criteria.frequency.length > 0 && (
                      <div className="p-3 bg-purple-50 border border-purple-200 rounded">
                        <p className="font-medium text-purple-800 text-sm mb-1">Frequency</p>
                        <ul className="text-sm text-purple-700 space-y-1">
                          {policy.criteria.frequency.map((item, i) => (
                            <li key={i}>• {item.text}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Covered Codes */}
              {policy.codes && Object.keys(policy.codes).length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-700 mb-2">Covered Codes</h4>
                  {Object.entries(policy.codes).map(([system, codes]) => (
                    <div key={system} className="mb-2">
                      <p className="text-xs text-gray-500 mb-1">{system}</p>
                      <div className="flex flex-wrap gap-2">
                        {codes.map((code, i) => (
                          <span
                            key={i}
                            className={`px-2 py-1 text-xs font-mono rounded ${
                              code.disposition === 'covered' ? 'bg-green-100 text-green-800' :
                              code.disposition === 'not_covered' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {code.code}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Compare View */}
      {activeView === 'compare' && (
        <div>
          <form onSubmit={handleCompare} className="mb-6">
            <div className="flex gap-2">
              <input
                type="text"
                value={compareCodes}
                onChange={(e) => setCompareCodes(e.target.value)}
                placeholder="Enter codes to compare (e.g., K0553, A9276)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {loading ? 'Comparing...' : 'Compare'}
              </button>
            </div>
          </form>

          <div className="mb-6">
            <p className="text-sm text-gray-500 mb-2">Quick compare:</p>
            <div className="flex flex-wrap gap-2">
              {quickCodes.map((code) => (
                <button
                  key={code}
                  onClick={() => {
                    setCompareCodes(code);
                    comparePolicies([code]).then(setComparison).catch(() => setError('Comparison failed'));
                  }}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm font-mono transition"
                >
                  {code}
                </button>
              ))}
            </div>
          </div>

          {comparison && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">
                Coverage Comparison: {comparison.procedure_codes.join(', ')}
              </h3>

              {comparison.jurisdictions.length === 0 ? (
                <p className="text-gray-500">No jurisdiction-specific policies found.</p>
              ) : (
                <div className="space-y-3">
                  {comparison.jurisdictions.map((j, i) => (
                    <div key={i} className="p-3 bg-gray-50 border border-gray-200 rounded flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-800">{j.jurisdiction}</p>
                        {j.mac_name && <p className="text-sm text-gray-500">{j.mac_name}</p>}
                        {j.notes && <p className="text-sm text-gray-600 mt-1">{j.notes}</p>}
                      </div>
                      <div className="flex items-center gap-2">
                        {j.policy_id && (
                          <span className="font-mono text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                            {j.policy_id}
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs rounded ${
                          j.disposition === 'covered' ? 'bg-green-100 text-green-800' :
                          j.disposition === 'not_covered' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {j.disposition}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Changes View */}
      {activeView === 'changes' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">Recent policy updates</p>
            <button
              onClick={loadChanges}
              disabled={loading}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm transition disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {changes.length === 0 && !loading ? (
            <p className="text-gray-500 text-center py-8">No recent changes found</p>
          ) : (
            <div className="space-y-3">
              {changes.map((change, i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-blue-600">{change.policy_id}</span>
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          change.change_type === 'created' ? 'bg-green-100 text-green-800' :
                          change.change_type === 'retired' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {change.change_type}
                        </span>
                      </div>
                      {change.title && <p className="text-gray-700 mt-1">{change.title}</p>}
                      {change.summary && <p className="text-sm text-gray-500 mt-1">{change.summary}</p>}
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(change.changed_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
