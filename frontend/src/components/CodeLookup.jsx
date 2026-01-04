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
            {selectedCode.medical_necessity_required && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                Medical Necessity Required
              </span>
            )}
          </div>

          <p className="text-gray-600 mb-4">{selectedCode.long_description}</p>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-gray-500">Category</p>
              <p className="text-gray-800">{selectedCode.category}</p>
            </div>
            <div>
              <p className="font-medium text-gray-500">Pricing Type</p>
              <p className="text-gray-800">{selectedCode.pricing_type}</p>
            </div>
            <div>
              <p className="font-medium text-gray-500">Common Modifiers</p>
              <div className="flex gap-1 flex-wrap">
                {selectedCode.common_modifiers.map((mod) => (
                  <span key={mod} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded font-mono text-xs">
                    {mod}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <p className="font-medium text-gray-500">LCD Reference</p>
              <p className="text-gray-800">{selectedCode.lcd_reference || 'N/A'}</p>
            </div>
          </div>

          {selectedCode.bundling_rules && selectedCode.bundling_rules.length > 0 && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded">
              <p className="font-medium text-amber-800 text-sm mb-1">Bundling Rules:</p>
              <ul className="text-sm text-amber-700 list-disc list-inside">
                {selectedCode.bundling_rules.map((rule, i) => (
                  <li key={i}>{rule}</li>
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
