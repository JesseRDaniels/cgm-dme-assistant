import { useState } from 'react';
import { generatePriorAuth } from '../api';

export default function PriorAuthGenerator() {
  const [formData, setFormData] = useState({
    patient: {
      first_name: '',
      last_name: '',
      dob: '',
      address: '',
      city: '',
      state: '',
      zip_code: '',
      phone: '',
      insurance_id: '',
    },
    device_type: '',
    diagnosis_codes: [''],
    a1c_value: '',
    insulin_regimen: '',
    hypoglycemia_history: '',
    additional_justification: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePatientChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      patient: { ...prev.patient, [field]: value },
    }));
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const data = {
        ...formData,
        diagnosis_codes: formData.diagnosis_codes.filter(dx => dx.trim()),
        a1c_value: formData.a1c_value ? parseFloat(formData.a1c_value) : null,
      };
      const response = await generatePriorAuth(data);
      setResult(response);
    } catch (err) {
      setError('Generation failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (result?.content) {
      navigator.clipboard.writeText(result.content);
    }
  };

  const devices = [
    'Dexcom G7',
    'Dexcom G6',
    'Freestyle Libre 3',
    'Freestyle Libre 2',
    'Medtronic Guardian 4',
  ];

  const states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Prior Authorization Generator</h2>
      <p className="text-gray-500 mb-6">Generate prior auth request letters based on LCD L33822</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Patient Information */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-medium text-gray-800 mb-4">Patient Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
                <input
                  type="text"
                  value={formData.patient.first_name}
                  onChange={(e) => handlePatientChange('first_name', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
                <input
                  type="text"
                  value={formData.patient.last_name}
                  onChange={(e) => handlePatientChange('last_name', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth *</label>
                <input
                  type="date"
                  value={formData.patient.dob}
                  onChange={(e) => handlePatientChange('dob', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Insurance ID</label>
                <input
                  type="text"
                  value={formData.patient.insurance_id}
                  onChange={(e) => handlePatientChange('insurance_id', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <input
                  type="text"
                  value={formData.patient.address}
                  onChange={(e) => handlePatientChange('address', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                <input
                  type="text"
                  value={formData.patient.city}
                  onChange={(e) => handlePatientChange('city', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-2">
                <div className="w-20">
                  <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                  <select
                    value={formData.patient.state}
                    onChange={(e) => handlePatientChange('state', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">--</option>
                    {states.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">ZIP</label>
                  <input
                    type="text"
                    value={formData.patient.zip_code}
                    onChange={(e) => handlePatientChange('zip_code', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Device & Diagnosis */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-medium text-gray-800 mb-4">Device & Diagnosis</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CGM Device *</label>
                <select
                  value={formData.device_type}
                  onChange={(e) => handleChange('device_type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select device...</option>
                  {devices.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
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
                  </div>
                ))}
                <button type="button" onClick={addDiagnosis} className="text-sm text-blue-600">
                  + Add diagnosis
                </button>
              </div>
            </div>
          </div>

          {/* Clinical Information */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-medium text-gray-800 mb-4">Clinical Information</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">A1C Value</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.a1c_value}
                    onChange={(e) => handleChange('a1c_value', e.target.value)}
                    placeholder="7.5"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Insulin Regimen</label>
                  <select
                    value={formData.insulin_regimen}
                    onChange={(e) => handleChange('insulin_regimen', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select...</option>
                    <option value="Insulin pump therapy">Insulin pump</option>
                    <option value="Multiple daily injections (4+ per day)">MDI (4+/day)</option>
                    <option value="Multiple daily injections (3 per day)">MDI (3/day)</option>
                    <option value="Basal-bolus regimen">Basal-bolus</option>
                    <option value="Basal insulin only">Basal only</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hypoglycemia History</label>
                <textarea
                  value={formData.hypoglycemia_history}
                  onChange={(e) => handleChange('hypoglycemia_history', e.target.value)}
                  placeholder="Document any severe or problematic hypoglycemic episodes..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Additional Justification</label>
                <textarea
                  value={formData.additional_justification}
                  onChange={(e) => handleChange('additional_justification', e.target.value)}
                  placeholder="Any additional clinical justification for CGM..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Generating...' : 'Generate Prior Auth Letter'}
          </button>
        </form>

        {/* Result */}
        <div>
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg mb-4">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-800">Generated Letter</h3>
                <button
                  onClick={copyToClipboard}
                  className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                >
                  📋 Copy
                </button>
              </div>
              <div className="p-4 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3 text-sm text-gray-500">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                    {result.document_type}
                  </span>
                  <span>Generated {result.metadata.generated_date}</span>
                </div>
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono bg-gray-50 p-4 rounded-lg overflow-auto max-h-[600px]">
                  {result.content}
                </pre>
              </div>
            </div>
          )}

          {!result && !error && (
            <div className="p-8 bg-gray-50 rounded-lg text-center text-gray-500 h-full flex flex-col items-center justify-center">
              <span className="text-4xl">📝</span>
              <p className="mt-2">Fill out the form to generate a prior authorization letter</p>
              <p className="text-sm mt-1">Based on LCD L33822 requirements</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
