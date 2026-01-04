import { useState, useCallback } from 'react';
import { uploadBatch, getBatchStatus, getBatchResults } from '../api';

export default function BatchUpload() {
  const [file, setFile] = useState(null);
  const [processingType, setProcessingType] = useState('scrub');
  const [batchId, setBatchId] = useState(null);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.name.endsWith('.csv')) {
      setFile(droppedFile);
      setError('');
    } else {
      setError('Please upload a CSV file');
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError('');
    setResults(null);
    setStatus(null);

    try {
      const response = await uploadBatch(file, processingType);
      setBatchId(response.batch_id);

      // Poll for status
      const pollStatus = async () => {
        const statusResponse = await getBatchStatus(response.batch_id);
        setStatus(statusResponse);

        if (statusResponse.status === 'completed') {
          const resultsResponse = await getBatchResults(response.batch_id);
          setResults(resultsResponse);
          setLoading(false);
        } else if (statusResponse.status === 'failed') {
          setError('Batch processing failed');
          setLoading(false);
        } else {
          setTimeout(pollStatus, 2000);
        }
      };

      pollStatus();
    } catch (err) {
      setError('Upload failed: ' + err.message);
      setLoading(false);
    }
  };

  const processingTypes = [
    { value: 'scrub', label: 'Claim Scrubbing', desc: 'Check claims for issues before submission' },
    { value: 'denial_analysis', label: 'Denial Analysis', desc: 'Analyze denials and get appeal recommendations' },
    { value: 'prior_auth', label: 'Prior Auth Check', desc: 'Generate prior auth checklists' },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Batch Processing</h2>

      {/* Processing Type Selection */}
      <div className="mb-6">
        <p className="text-sm font-medium text-gray-700 mb-3">Processing Type:</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {processingTypes.map((type) => (
            <button
              key={type.value}
              onClick={() => setProcessingType(type.value)}
              className={`p-4 border rounded-lg text-left transition ${
                processingType === type.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <p className="font-medium text-gray-800">{type.label}</p>
              <p className="text-sm text-gray-500">{type.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* File Upload */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition ${
          file ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        {file ? (
          <div>
            <svg className="mx-auto h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-2 text-gray-700 font-medium">{file.name}</p>
            <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
            <button
              onClick={() => setFile(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-700"
            >
              Remove
            </button>
          </div>
        ) : (
          <div>
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mt-2 text-gray-600">Drag and drop a CSV file, or</p>
            <label className="mt-2 inline-block px-4 py-2 bg-white border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition">
              <span className="text-blue-600 font-medium">Browse files</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>
        )}
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="mt-4 w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {loading ? 'Processing...' : 'Process File'}
      </button>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Status */}
      {status && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-gray-700">Processing Status</span>
            <span className={`px-2 py-1 rounded text-sm ${
              status.status === 'completed' ? 'bg-green-100 text-green-700' :
              status.status === 'failed' ? 'bg-red-100 text-red-700' :
              'bg-yellow-100 text-yellow-700'
            }`}>
              {status.status}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${(status.processed_rows / status.total_rows) * 100}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-gray-500">
            {status.processed_rows} / {status.total_rows} rows processed
            {status.errors > 0 && ` (${status.errors} errors)`}
          </p>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="mt-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">Results</h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {results.results.map((result, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg border ${
                  result.status === 'success' ? 'bg-white border-gray-200' : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-500">Row {result.row + 1}</span>
                  <span className={`text-sm ${result.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                    {result.status}
                  </span>
                </div>
                {result.result && (
                  <div className="text-sm text-gray-700">
                    {typeof result.result === 'object' ? (
                      <pre className="whitespace-pre-wrap">{JSON.stringify(result.result, null, 2)}</pre>
                    ) : (
                      result.result
                    )}
                  </div>
                )}
                {result.error && (
                  <p className="text-sm text-red-600">{result.error}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
