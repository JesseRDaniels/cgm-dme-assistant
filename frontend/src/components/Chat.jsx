import { useState, useRef, useEffect } from 'react';
import { chat } from '../api';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chat(userMessage);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        intent: response.intent,
        confidence: response.confidence,
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'error',
        content: 'Failed to get response. Make sure the API is running.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const exampleQueries = [
    "What HCPCS code for CGM sensors?",
    "What causes a CO-4 denial?",
    "What documentation is needed for prior auth?",
    "Can I bill A9276 and K0553 together?",
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <h2 className="text-2xl font-bold text-gray-700 mb-2">CGM DME Assistant</h2>
            <p className="text-gray-500 mb-6">Ask me about CGM billing, prior auth, denials, or codes</p>
            <div className="flex flex-wrap justify-center gap-2">
              {exampleQueries.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:border-blue-300 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.role === 'error'
                  ? 'bg-red-50 text-red-700 border border-red-200'
                  : 'bg-white border border-gray-200'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 text-xs text-gray-500">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                    {msg.intent}
                  </span>
                  <span>
                    {Math.round(msg.confidence * 100)}% confidence
                  </span>
                </div>
              )}
              <div className="prose prose-sm max-w-none whitespace-pre-wrap">
                {msg.content}
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-500 mb-2">Sources:</p>
                  <div className="space-y-1">
                    {msg.citations.slice(0, 3).map((cite, j) => (
                      <div key={j} className="text-xs text-gray-500">
                        [{j + 1}] {cite.source}
                        {cite.section && ` - ${cite.section}`}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
              <div className="flex items-center gap-2 text-gray-500">
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                Thinking...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about CGM billing, codes, denials..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
