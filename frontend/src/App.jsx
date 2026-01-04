import { useState } from 'react';
import Chat from './components/Chat';
import CodeLookup from './components/CodeLookup';
import BatchUpload from './components/BatchUpload';

function App() {
  const [activeTab, setActiveTab] = useState('chat');

  const tabs = [
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'codes', label: 'Codes', icon: '📋' },
    { id: 'batch', label: 'Batch', icon: '📤' },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">C</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">CGM DME Assistant</h1>
              <p className="text-sm text-gray-500">Billing, Prior Auth, Denials</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex gap-1 bg-gray-100 p-1 rounded-lg">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                  activeTab === tab.id
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {activeTab === 'chat' && <Chat />}
        {activeTab === 'codes' && <CodeLookup />}
        {activeTab === 'batch' && <BatchUpload />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-3 px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-sm text-gray-500">
          <span>CGM DME Assistant v0.1</span>
          <span>API: localhost:8001</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
