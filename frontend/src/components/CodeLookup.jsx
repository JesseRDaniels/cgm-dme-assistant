import { useState } from 'react';
import { lookupCode, searchCodes } from '../api';

export default function CodeLookup() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [selectedCode, setSelectedCode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setSelectedCode(null);

    try {
      // Check if it's a specific code (starts with letter + numbers)
      if (/^[A-Za-z]\d+/.test(query.trim())) {
        const code = await lookupCode(query.trim().toUpperCase());
        setSelectedCode(code);
        setResults([]);
      } else {
        const data = await searchCodes(query);
        setResults(data.results);
      }
    } catch (err) {
      setError('Code not found or search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const quickCodes = ['A9276', 'A9277', 'A9278', 'K0553', 'K0554'];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">HCPCS Code Lookup</h2>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter code (A9276) or search term (sensor)"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {/* Quick codes */}
      <div className="mb-6">
        <p className="text-sm text-gray-500 mb-2">Quick lookup:</p>
        <div className="flex flex-wrap gap-2">
          {quickCodes.map((code) => (
            <button
              key={code}
              onClick={() => {
                setQuery(code);
                lookupCode(code).then(setSelectedCode).catch(() => setError('Code not found'));
              }}
              className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm font-mono transition"
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Selected Code Detail */}
      {selectedCode && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold font-mono text-blue-600">{selectedCode.code}</h3>
              <p className="text-lg text-gray-700">{selectedCode.short_description}</p>
            </div>
            <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
              {selectedCode.code_system || 'HCPCS'}
            </span>
          </div>

          <p className="text-gray-600 mb-4">{selectedCode.description}</p>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-gray-500">Category</p>
              <p className="text-gray-800 capitalize">{selectedCode.category || 'N/A'}</p>
            </div>
            <div>
              <p className="font-medium text-gray-500">Status</p>
              <p className="text-gray-800">{selectedCode.is_active ? 'Active' : 'Inactive'}</p>
            </div>
          </div>

          {/* RVU Info */}
          {selectedCode.rvu && (
            <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded">
              <p className="font-medium text-gray-700 text-sm mb-2">RVU Information</p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div><span className="text-gray-500">Work:</span> {selectedCode.rvu.work_rvu}</div>
                <div><span className="text-gray-500">PE (Non-Fac):</span> {selectedCode.rvu.pe_rvu_nonfacility}</div>
                <div><span className="text-gray-500">Total:</span> {selectedCode.rvu.total_rvu_nonfacility}</div>
              </div>
            </div>
          )}

          {/* Policies */}
          {selectedCode.policies && selectedCode.policies.length > 0 && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <p className="font-medium text-blue-800 text-sm mb-2">Coverage Policies:</p>
              <ul className="text-sm text-blue-700 space-y-1">
                {selectedCode.policies.map((policy, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="font-mono text-xs bg-blue-100 px-1 rounded">{policy.policy_id}</span>
                    <span>{policy.title}</span>
                    <span className={`text-xs px-1 rounded ${policy.disposition === 'covered' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {policy.disposition}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">{results.length} results found</p>
          {results.map((code) => (
            <div
              key={code.code}
              onClick={() => setSelectedCode(code)}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 cursor-pointer transition"
            >
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold text-blue-600">{code.code}</span>
                <span className="text-gray-700">{code.short_description}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
