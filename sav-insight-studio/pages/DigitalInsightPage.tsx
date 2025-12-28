import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageCircle, Send, Loader2, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/apiService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const DigitalInsightPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);

  useEffect(() => {
    // Get dataset ID from localStorage (same way other pages do it)
    const storedDatasetId = localStorage.getItem('currentDatasetId');
    const storedMeta = localStorage.getItem('currentDatasetMeta');
    
    if (storedDatasetId) {
      setDatasetId(storedDatasetId);
    } else if (storedMeta) {
      try {
        const meta = JSON.parse(storedMeta);
        if (meta.id) {
          setDatasetId(meta.id);
        }
      } catch (e) {
        console.error('Failed to parse dataset meta:', e);
      }
    }
    
    // Add welcome message
    setMessages([{
      id: '1',
      role: 'assistant',
      content: 'Merhaba! Verileriniz hakkında sorular sorabilirsiniz. Size nasıl yardımcı olabilirim?',
      timestamp: new Date()
    }]);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    // Get dataset ID from state or localStorage (same way other pages do it)
    const currentDatasetId = datasetId || localStorage.getItem('currentDatasetId') || 
      (() => {
        const meta = localStorage.getItem('currentDatasetMeta');
        if (meta) {
          try {
            const parsed = JSON.parse(meta);
            return parsed.id;
          } catch (e) {
            return null;
          }
        }
        return null;
      })();
    
    if (!currentDatasetId) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Veri seti bulunamadı. Lütfen önce bir veri seti seçin.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiService.askQuestion(currentDatasetId, input);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer || 'Üzgünüm, bir hata oluştu.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dijital Insight</h1>
            <p className="text-gray-600 mt-1">Verileriniz hakkında sorular sorun, AI destekli cevaplar alın</p>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex items-start space-x-3 max-w-3xl ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white'
                  }`}
                >
                  {message.role === 'user' ? (
                    <MessageCircle className="w-4 h-4" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                </div>
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString('tr-TR', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-start space-x-3 max-w-3xl">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="rounded-2xl px-4 py-3 bg-gray-100">
                  <div className="flex items-center space-x-2">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
                    <span className="text-sm text-gray-600">Düşünüyor...</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Verileriniz hakkında bir soru sorun..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                disabled={loading}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl hover:from-purple-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center space-x-2 shadow-sm"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>Gönder</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <div className="flex items-start space-x-3">
          <Sparkles className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-900 mb-1">AI Destekli Analiz</p>
            <p className="text-xs text-blue-700">
              Bu özellik şu anda geliştirme aşamasındadır. İleride embedding ve gelişmiş AI modelleri ile daha detaylı analizler yapabileceksiniz.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DigitalInsightPage;

