import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MessageCircle, Send, Loader2, Sparkles, BarChart3, ArrowLeft, Lightbulb, Users } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import apiService from '../services/apiService';

interface ThreadQuestion {
  id: number;
  question_text: string;
  normalized_question: string;
  mode: string;
  status: string;
  created_at?: string;
  mapped_variable_ids?: number[];
  result?: {
    id: number;
    narrative_text?: string;
    evidence_json?: any;
    chart_json?: any;
    mapping_debug_json?: any;
    created_at?: string;
  };
}

interface Thread {
  id: string;
  dataset_id: string;
  audience_id?: string;
  title: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  questions: ThreadQuestion[];
}

interface SuggestedQuestion {
  question_text: string;
  variable_code?: string;
  category: string;
}

const ThreadChatPage: React.FC = () => {
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const [thread, setThread] = useState<Thread | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<Record<string, SuggestedQuestion[]>>({});
  const [showSuggested, setShowSuggested] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (threadId) {
      loadThread(true); // Initial load
    }
  }, [threadId]);

  useEffect(() => {
    if (thread) {
      loadSuggestedQuestions();
    }
  }, [thread]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thread?.questions]);

  // Polling for processing questions
  useEffect(() => {
    if (!thread) return;

    const hasProcessing = thread.questions.some(q => q.status === 'processing');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadThread(false); // Polling, not initial load
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [thread]);

  const loadThread = async (isInitial = false) => {
    if (!threadId) return;

    try {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);
      const data = await apiService.getThread(threadId);
      setThread(data);
    } catch (err: any) {
      setError(err.message || 'Thread yüklenirken hata oluştu');
      console.error('Error loading thread:', err);
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  };

  const loadSuggestedQuestions = async () => {
    if (!thread) return;

    try {
      const data = await apiService.getSuggestedQuestions(
        thread.dataset_id,
        thread.audience_id
      );
      setSuggestedQuestions(data);
    } catch (err: any) {
      console.error('Error loading suggested questions:', err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || submitting || !threadId) return;

    const questionText = input;
    setInput('');
    setSubmitting(true);

    try {
      // Add question via API (this will process it and return result)
      await apiService.addThreadQuestion(threadId, questionText);

      // Reload thread to get the result
      await loadThread(false);
    } catch (err: any) {
      setError(err.message || 'Soru gönderilirken hata oluştu');
      console.error('Error sending question:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSuggestedQuestion = (questionText: string) => {
    setInput(questionText);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderChart = (chartJson: any) => {
    if (!chartJson || !chartJson.data) return null;

    const { labels, datasets } = chartJson.data;
    if (!labels || !datasets || datasets.length === 0) return null;

    // Convert chart.js format to Recharts format
    const chartData = labels.map((label: string, index: number) => {
      const dataPoint: any = { label };
      datasets.forEach((dataset: any) => {
        dataPoint[dataset.label || 'value'] = dataset.data[index] || 0;
      });
      return dataPoint;
    });

    // If single dataset, use simple bar chart
    if (datasets.length === 1) {
      const dataKey = datasets[0].label || 'value';
      const maxValue = Math.max(...datasets[0].data);

      return (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-5 h-5 text-purple-600" />
            <h3 className="font-semibold text-gray-900">Grafik</h3>
          </div>
          <div className="space-y-2">
            {labels.map((label: string, index: number) => {
              const value = datasets[0].data[index];
              const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;
              return (
                <div key={index} className="flex items-center gap-3">
                  <div className="w-32 text-sm text-gray-600 truncate">{label}</div>
                  <div className="flex-1 bg-gray-200 rounded-full h-6 relative overflow-hidden">
                    <div
                      className="bg-purple-600 h-full rounded-full transition-all"
                      style={{ width: `${percentage}%` }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center text-xs font-medium text-gray-700">
                      {value}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    // Multiple datasets (breakdown/comparison) - use Recharts grouped bar chart
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-5 h-5 text-purple-600" />
          <h3 className="font-semibold text-gray-900">Grafik</h3>
        </div>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 120, right: 40, top: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
              <XAxis type="number" />
              <YAxis 
                type="category" 
                dataKey="label" 
                width={110}
                tick={{ fontSize: 11 }}
                interval={0}
                tickFormatter={(value: string) => {
                  return value.length > 25 ? value.substring(0, 23) + '...' : value;
                }}
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
              />
              <Legend />
              {datasets.map((dataset: any, index: number) => (
                <Bar 
                  key={dataset.label || `dataset-${index}`}
                  dataKey={dataset.label || 'value'} 
                  fill={dataset.backgroundColor || `rgba(${54 + index * 50}, 162, 235, 0.6)`}
                  radius={[0, 4, 4, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (error && !thread) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto text-center text-gray-500">
          Thread bulunamadı
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/threads')}
                className="text-gray-600 hover:text-gray-900 p-2 hover:bg-gray-100 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{thread.title}</h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                  {thread.audience_id && (
                    <div className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      <span>Audience: {thread.audience_id}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {thread.questions.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p>Henüz soru eklenmemiş. İlk sorunuzu sorun!</p>
            </div>
          ) : (
            thread.questions.map((question) => (
              <div key={question.id} className="space-y-4">
                {/* User Question */}
                <div className="flex justify-end">
                  <div className="max-w-3xl">
                    <div className="bg-blue-500 text-white rounded-2xl px-4 py-3">
                      <p className="text-sm whitespace-pre-wrap">{question.question_text}</p>
                    </div>
                    {question.mode && (
                      <p className="text-xs text-gray-500 mt-1 text-right">
                        Mode: {question.mode}
                      </p>
                    )}
                  </div>
                </div>

                {/* Assistant Response */}
                {question.result ? (
                  <div className="flex justify-start">
                    <div className="max-w-3xl w-full">
                      <div className="bg-gray-100 rounded-2xl px-4 py-3">
                        {question.result.narrative_text && (
                          <div className="mb-3">
                            <p className="text-sm text-gray-900 whitespace-pre-wrap">
                              {question.result.narrative_text}
                            </p>
                          </div>
                        )}
                        {question.result.chart_json && renderChart(question.result.chart_json)}
                        {question.result.evidence_json && (
                          <details className="mt-3">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900 font-medium">
                              📊 Evidence Details
                            </summary>
                            <div className="mt-2 text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                              <pre className="whitespace-pre-wrap">{JSON.stringify(question.result.evidence_json, null, 2)}</pre>
                            </div>
                          </details>
                        )}
                        {question.result.mapping_debug_json && (
                          <details className="mt-3">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900 font-medium">
                              🔍 Mapping Debug
                            </summary>
                            <div className="mt-2 text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                              <pre className="whitespace-pre-wrap">{JSON.stringify(question.result.mapping_debug_json, null, 2)}</pre>
                            </div>
                          </details>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {question.result.created_at &&
                          new Date(question.result.created_at).toLocaleString('tr-TR')}
                      </p>
                    </div>
                  </div>
                ) : question.status === 'processing' ? (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-2xl px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
                        <span className="text-sm text-gray-600">İşleniyor...</span>
                      </div>
                    </div>
                  </div>
                ) : question.status === 'error' ? (
                  <div className="flex justify-start">
                    <div className="bg-red-50 border border-red-200 rounded-2xl px-4 py-3">
                      <p className="text-sm text-red-700">Hata oluştu</p>
                    </div>
                  </div>
                ) : null}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Bir soru sorun..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                rows={2}
                disabled={submitting}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={submitting || !input.trim()}
              className="px-6 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              {submitting ? (
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

      {/* Suggested Questions Sidebar */}
      {showSuggested && (
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto flex flex-col">
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-600" />
                <h2 className="font-semibold text-gray-900">Önerilen Sorular</h2>
              </div>
              <button
                onClick={() => setShowSuggested(false)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                ×
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {Object.keys(suggestedQuestions).length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8">
                Önerilen soru bulunamadı
              </div>
            ) : (
              Object.entries(suggestedQuestions).map(([category, questions]) => (
                <div key={category}>
                  <h3 className="text-sm font-medium text-gray-700 mb-2 capitalize">
                    {category === 'demographics' ? 'Demografikler' :
                     category === 'kpis' ? 'KPI\'lar' :
                     category === 'drivers' ? 'Sürücüler' :
                     category === 'comparisons' ? 'Karşılaştırmalar' :
                     category}
                  </h3>
                  <div className="space-y-2">
                    {questions.slice(0, 5).map((sq, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestedQuestion(sq.question_text)}
                        className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-purple-50 hover:text-purple-700 rounded-lg transition-colors border border-transparent hover:border-purple-200"
                      >
                        {sq.question_text}
                      </button>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
      
      {/* Show Suggested Questions Button when hidden */}
      {!showSuggested && (
        <button
          onClick={() => setShowSuggested(true)}
          className="fixed right-4 bottom-20 bg-purple-600 text-white p-3 rounded-full shadow-lg hover:bg-purple-700 transition-colors z-10"
          title="Önerilen Soruları Göster"
        >
          <Lightbulb className="w-5 h-5" />
        </button>
      )}
    </div>
  );
};

export default ThreadChatPage;

