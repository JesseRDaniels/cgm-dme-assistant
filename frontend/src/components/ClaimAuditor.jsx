import { useState } from 'react';
import { auditClaim } from '../api';

export default function ClaimAuditor() {
  const [formData, setFormData] = useState({
    hcpcs_code: '',
    modifier: '',
    diagnosis_codes: [''],
    device_type: '',
    has_face_to_face: false,
    has_written_order: false,
    has_medical_necessity: false,
    insulin_therapy: '',
    a1c_documented: false,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleDiagnosisChange = (index, value) => {
    const newDx = [...formData.diagnosis_codes];
    newDx[index] = value;
    setFormData(prev => ({ ...prev, diagnosis_codes: newDx }));
  };

  const addDiagnosis = () => {
    setFormData(prev => ({
      ...prev,
      diagnosis_codes: [...prev.diagnosis_codes, ''],
    }));
  };

  const removeDiagnosis = (index) => {
    setFormData(prev => ({
      ...prev,
      diagnosis_codes: prev.diagnosis_codes.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const data = {
        ...formData,
        diagnosis_codes: formData.diagnosis_codes.filter(dx => dx.trim()),
      };
      const response = await auditClaim(data);
      setResult(response);
    } catch (err) {
      setError('Audit failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const cgmCodes = ['A9276', 'A9277', 'A9278', 'K0553', 'K0554'];
  const modifiers = ['KX', 'NU', 'RR', 'KX,NU', 'KX,RR'];
  const devices = ['Dexcom G7', 'Dexcom G6', 'Freestyle Libre 3', 'Freestyle Libre 2', 'Medtronic Guardian'];

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'error': return 'bg-red-50 border-red-200 text-red-700';
      case 'warning': return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      case 'info': return 'bg-blue-50 border-blue-200 text-blue-700';
      default: return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return '•';
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Claim Auditor</h2>
      <p className="text-gray-500 mb-6">Validate CGM claims against LCD L33822 before submission</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* HCPCS Code */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">HCPCS Code *</label>
            <div className="flex gap-2">
              <select
                value={formData.hcpcs_code}
                onChange={(e) => handleChange('hcpcs_code', e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select code...</option>
                {cgmCodes.map(code => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
              <input
                type="text"
                value={formData.hcpcs_code}
                onChange={(e) => handleChange('hcpcs_code', e.target.value.toUpperCase())}
                placeholder="Or type"
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Modifier */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Modifier(s)</label>
            <select
              value={formData.modifier}
              onChange={(e) => handleChange('modifier', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">No modifier</option>
              {modifiers.map(mod => (
                <option key={mod} value={mod}>{mod}</option>
              ))}
            </select>
          </div>

          {/* Diagnosis Codes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Diagnosis Codes (ICD-10) *</label>
            {formData.diagnosis_codes.map((dx, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={dx}
                  onChange={(e) => handleDiagnosisChange(i, e.target.value.toUpperCase())}
                  placeholder="E11.65"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                {formData.diagnosis_codes.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeDiagnosis(i)}
                    className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addDiagnosis}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              + Add diagnosis
            </button>
          </div>

          {/* Device */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Device Type</label>
            <select
              value={formData.device_type}
              onChange={(e) => handleChange('device_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select device...</option>
              {devices.map(device => (
                <option key={device} value={device}>{device}</option>
              ))}
            </select>
          </div>

          {/* Documentation Checklist */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-3">Documentation on File:</p>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.has_face_to_face}
                  onChange={(e) => handleChange('has_face_to_face', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Face-to-face encounter (within 6 months)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.has_written_order}
                  onChange={(e) => handleChange('has_written_order', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Detailed Written Order (DWO)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.has_medical_necessity}
                  onChange={(e) => handleChange('has_medical_necessity', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Medical necessity statement</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.a1c_documented}
                  onChange={(e) => handleChange('a1c_documented', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">A1C value documented</span>
              </label>
            </div>
          </div>

          {/* Insulin Therapy */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Insulin Therapy</label>
            <select
              value={formData.insulin_therapy}
              onChange={(e) => handleChange('insulin_therapy', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select...</option>
              <option value="pump">Insulin pump</option>
              <option value="mdi">Multiple daily injections (3+)</option>
              <option value="basal_only">Basal insulin only</option>
              <option value="none">No insulin</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading || !formData.hcpcs_code}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Auditing...' : 'Audit Claim'}
          </button>
        </form>

        {/* Results */}
        <div>
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg mb-4">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Score Card */}
              <div className={`p-6 rounded-lg border-2 ${result.passed ? 'border-green-400 bg-green-50' : 'border-red-400 bg-red-50'}`}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm text-gray-500">Audit Score</p>
                    <p className={`text-4xl font-bold ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                      {result.score}/100
                    </p>
                  </div>
                  <div className={`px-4 py-2 rounded-lg font-medium ${result.passed ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                    {result.passed ? '✓ PASS' : '✗ FAIL'}
                  </div>
                </div>
                <p className="text-gray-700">{result.summary}</p>
                <p className="text-sm text-gray-500 mt-2">LCD Reference: {result.lcd_reference}</p>
              </div>

              {/* Issues */}
              {result.issues.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-800 mb-3">
                    Issues Found ({result.issues.length})
                  </h3>
                  <div className="space-y-3">
                    {result.issues.map((issue, i) => (
                      <div
                        key={i}
                        className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-lg">{getSeverityIcon(issue.severity)}</span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium uppercase px-2 py-0.5 bg-white/50 rounded">
                                {issue.category}
                              </span>
                              <span className="text-xs uppercase">
                                {issue.severity}
                              </span>
                            </div>
                            <p className="font-medium">{issue.message}</p>
                            <p className="text-sm mt-1 opacity-80">
                              💡 {issue.recommendation}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.passed && result.issues.length === 0 && (
                <div className="p-6 bg-green-50 border border-green-200 rounded-lg text-center">
                  <span className="text-4xl">✅</span>
                  <p className="text-green-700 font-medium mt-2">All checks passed!</p>
                  <p className="text-green-600 text-sm">This claim is ready for submission.</p>
                </div>
              )}
            </div>
          )}

          {!result && !error && (
            <div className="p-8 bg-gray-50 rounded-lg text-center text-gray-500">
              <span className="text-4xl">🔍</span>
              <p className="mt-2">Fill out the form and click "Audit Claim"</p>
              <p className="text-sm">We'll check LCD L33822 compliance</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
