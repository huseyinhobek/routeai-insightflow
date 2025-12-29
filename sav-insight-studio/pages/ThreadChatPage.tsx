import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MessageCircle, Send, Loader2, Sparkles, BarChart3, ArrowLeft, Lightbulb, Users, CheckCircle2, AlertCircle, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
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
    proxy_answer?: any;
    decision_rules?: any[];
    clarifying_controls?: any;
    next_best_questions?: string[];
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
  const [selectedDecisionRule, setSelectedDecisionRule] = useState<Record<number, string>>({});
  const [decisionGoal, setDecisionGoal] = useState<Record<number, string>>({});
  const [confidenceThreshold, setConfidenceThreshold] = useState<Record<number, number>>({});

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

  const handleNextBestQuestion = async (questionText: string) => {
    if (!threadId || submitting) return;
    
    setInput('');
    setSubmitting(true);

    try {
      await apiService.addThreadQuestion(threadId, questionText);
      await loadThread(false);
    } catch (err: any) {
      setError(err.message || 'Soru gönderilirken hata oluştu');
      console.error('Error sending question:', err);
    } finally {
      setSubmitting(false);
    }
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

  const renderDecisionProxy = (question: ThreadQuestion) => {
    if (!question.result || question.mode !== 'decision_proxy') return null;

    const evidence = question.result.evidence_json || {};
    const proxyAnswer = evidence.proxy_answer || {};
    const decisionRules = evidence.decision_rules || [];
    const clarifyingControls = evidence.clarifying_controls || {};
    const nextBestQuestions = evidence.next_best_questions || [];
    const distribution = evidence.distribution;
    const comparison = evidence.comparison;

    // Debug: Log to console to verify data structure
    console.log('Decision Proxy Data:', {
      hasEvidence: !!evidence,
      hasProxyAnswer: !!proxyAnswer,
      decisionRulesCount: decisionRules.length,
      hasClarifyingControls: Object.keys(clarifyingControls).length > 0,
      nextBestQuestionsCount: nextBestQuestions.length,
      hasDistribution: !!distribution,
      hasComparison: !!comparison,
      evidenceKeys: Object.keys(evidence)
    });

    const questionId = question.id;
    const currentRule = selectedDecisionRule[questionId] || '';
    const currentGoal = decisionGoal[questionId] || clarifyingControls.decision_goal?.default || 'cost';
    const currentConfidence = confidenceThreshold[questionId] || clarifyingControls.confidence_threshold?.default || 60;

    const proxyHeader = proxyAnswer.proxy_header || {};
    const proxyCopy = proxyAnswer.proxy_copy || {};
    const isProxy = proxyHeader.is_proxy || false;
    const proxyVarCode = proxyHeader.proxy_var_code;
    const proxyConfidence = proxyHeader.confidence;
    const proxyTier = proxyHeader.tier;
    const proxyTierName = proxyHeader.tier_name || proxyCopy.tier_name;
    const alternatives = proxyHeader.alternatives || [];
    
    // Get copy fields (with fallbacks)
    const bannerTitle = proxyCopy.banner_title || proxyHeader.message || "Not directly measured → using proxy";
    const limitationStatement = proxyCopy.limitation_statement || "Using proxy variable";
    const whatWeCannotClaim = proxyCopy.what_we_cannot_claim || [];
    const severity = proxyCopy.severity || 'info';
    
    // Tier badge colors
    const getTierBadgeColor = (tier: number | undefined) => {
      if (tier === 0) return 'bg-green-100 text-green-800 border-green-300';
      if (tier === 1) return 'bg-blue-100 text-blue-800 border-blue-300';
      if (tier === 2) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      if (tier === 3) return 'bg-orange-100 text-orange-800 border-orange-300';
      return 'bg-gray-100 text-gray-800 border-gray-300';
    };
    
    const getTierLabel = (tier: number | undefined) => {
      if (tier === 0) return 'Tier0: Direct';
      if (tier === 1) return 'Tier1: Behavioral';
      if (tier === 2) return 'Tier2: Attitudinal';
      if (tier === 3) return 'Tier3: Knowledge';
      return 'Unknown Tier';
    };
    
    // Severity-based styling
    const getSeverityStyles = (sev: string) => {
      if (sev === 'risk') return 'bg-red-50 border-l-4 border-red-500';
      if (sev === 'warn') return 'bg-orange-50 border-l-4 border-orange-500';
      return 'bg-blue-50 border-l-4 border-blue-500';
    };
    
    const getSeverityIconColor = (sev: string) => {
      if (sev === 'risk') return 'text-red-600';
      if (sev === 'warn') return 'text-orange-600';
      return 'text-blue-600';
    };

    return (
      <div className="space-y-4">
        {/* Measurement Boundary Banner */}
        {isProxy && (
          <div className={`${getSeverityStyles(severity)} p-4 rounded-r-lg`}>
            <div className="flex items-start gap-2">
              <AlertCircle className={`w-5 h-5 ${getSeverityIconColor(severity)} flex-shrink-0 mt-0.5`} />
              <div className="flex-1">
                {/* Banner Title + Tier Badge */}
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <p className={`text-sm font-semibold ${severity === 'risk' ? 'text-red-900' : severity === 'warn' ? 'text-orange-900' : 'text-blue-900'}`}>
                    {bannerTitle}
                  </p>
                  {proxyTier !== undefined && (
                    <span className={`text-xs px-2 py-0.5 rounded border ${getTierBadgeColor(proxyTier)}`}>
                      {getTierLabel(proxyTier)}
                    </span>
                  )}
                  {proxyConfidence !== undefined && (
                    <span className="text-xs text-gray-600">
                      (confidence: {(proxyConfidence * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>
                
                {/* Proxy Variable Info */}
                {proxyVarCode && (
                  <p className={`text-xs ${severity === 'risk' ? 'text-red-700' : severity === 'warn' ? 'text-orange-700' : 'text-blue-700'} mb-2`}>
                    Proxy variable: <span className="font-mono font-semibold">{proxyVarCode}</span>
                  </p>
                )}
                
                {/* Limitation Statement (Always Visible) */}
                <p className={`text-sm ${severity === 'risk' ? 'text-red-800' : severity === 'warn' ? 'text-orange-800' : 'text-blue-800'} mb-3 font-medium`}>
                  {limitationStatement}
                </p>
                
                {/* What We Cannot Claim (Expandable) */}
                {whatWeCannotClaim.length > 0 && (
                  <details className="mb-2">
                    <summary className="text-xs font-medium cursor-pointer hover:underline mb-1">
                      What we cannot claim
                    </summary>
                    <ul className="list-disc list-inside text-xs space-y-1 mt-1 ml-2">
                      {whatWeCannotClaim.map((claim: string, idx: number) => (
                        <li key={idx} className={severity === 'risk' ? 'text-red-700' : severity === 'warn' ? 'text-orange-700' : 'text-blue-700'}>
                          {claim}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                
                {/* Alternatives */}
                {alternatives.length > 0 && (
                  <div className="mt-2">
                    <p className={`text-xs ${severity === 'risk' ? 'text-red-600' : severity === 'warn' ? 'text-orange-600' : 'text-blue-600'} mb-1`}>Alternative proxies:</p>
                    <div className="flex flex-wrap gap-2">
                      {alternatives.map((alt: any, idx: number) => (
                        <span key={idx} className={`text-xs px-2 py-1 rounded font-mono border ${getTierBadgeColor(alt.tier)}`}>
                          {alt.var_code} (Tier{alt.tier}, {(alt.confidence * 100).toFixed(0)}%)
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Narrative */}
        {question.result.narrative_text && (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
            <p className="text-sm text-gray-900 whitespace-pre-wrap">
              {question.result.narrative_text}
            </p>
          </div>
        )}

        {/* What We Can Measure - Show if distribution or comparison exists */}
        {(distribution || comparison) && (
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-600" />
              Ne Ölçebiliriz?
            </h3>
            <div className="space-y-4">
              {/* Distribution Chart */}
              {distribution && distribution.categories && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Dağılım</h4>
                  <div className="bg-white rounded-lg p-4">
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={distribution.categories.map((cat: any) => ({
                        label: cat.label,
                        value: cat.percent,
                        count: cat.count
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" angle={-45} textAnchor="end" height={100} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="value" fill="#9333ea" radius={[4, 4, 0, 0]}>
                          {distribution.categories.map((_: any, index: number) => (
                            <Cell key={`cell-${index}`} fill={`rgba(147, 51, 234, ${0.6 + (index * 0.1)})`} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Comparison Chart */}
              {comparison && comparison.comparison_type === 'audience_vs_total' && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Audience vs Total Karşılaştırması</h4>
                  <div className="bg-white rounded-lg p-4">
                    {comparison.delta_pp && comparison.delta_pp.length > 0 && (
                      <div className="space-y-2 mb-4">
                        {comparison.delta_pp.map((delta: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                            <span className="text-sm text-gray-700">{delta.option}</span>
                            <div className="flex items-center gap-4">
                              <span className="text-xs text-gray-500">Audience: {delta.audience_percent.toFixed(1)}%</span>
                              <span className="text-xs text-gray-500">Total: {delta.overall_percent.toFixed(1)}%</span>
                              <span className={`text-sm font-semibold ${delta.diff_pp >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {delta.diff_pp >= 0 ? '+' : ''}{delta.diff_pp.toFixed(1)}pp
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {comparison.audience && comparison.total && (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={comparison.audience.categories?.map((cat: any, idx: number) => {
                          const totalCat = comparison.total.categories?.find((tc: any) => tc.label === cat.label);
                          return {
                            label: cat.label,
                            audience: cat.percent,
                            total: totalCat?.percent || 0
                          };
                        }) || []}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="label" angle={-45} textAnchor="end" height={100} />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="audience" fill="#3b82f6" name="Audience" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="total" fill="#ef4444" name="Total" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Decision Rules */}
        {decisionRules.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600" />
              Karar Kuralları (Varsayımlar)
            </h3>
            <p className="text-xs text-gray-600 mb-4">
              Lütfen bir karar kuralı seçin. Her kural farklı bir varsayıma dayanır.
            </p>
            <div className="space-y-3">
              {decisionRules.map((rule: any) => (
                <label
                  key={rule.id}
                  className={`block p-3 border-2 rounded-lg cursor-pointer transition-all ${
                    currentRule === rule.id
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 bg-white hover:border-purple-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="radio"
                      name={`decision-rule-${questionId}`}
                      value={rule.id}
                      checked={currentRule === rule.id}
                      onChange={(e) => setSelectedDecisionRule({ ...selectedDecisionRule, [questionId]: e.target.value })}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 mb-1">{rule.title}</div>
                      <div className="text-xs text-gray-600 mb-2">{rule.assumption}</div>
                      <div className="text-xs text-gray-500 mb-2">
                        <strong>Nasıl uygulanır:</strong> {rule.how_to_apply}
                      </div>
                      {rule.result_preview && (
                        <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
                          <strong>Önizleme:</strong>{' '}
                          {rule.result_preview.top_option && (
                            <span className="text-purple-600 font-semibold">
                              {rule.result_preview.top_option}
                            </span>
                          )}
                          {rule.result_preview.supporting_metric && (
                            <span className="text-gray-600 ml-2">
                              ({rule.result_preview.supporting_metric})
                            </span>
                          )}
                          {rule.result_preview.recommendation && (
                            <span className="text-purple-600 font-semibold">
                              {rule.result_preview.recommendation}
                            </span>
                          )}
                          {rule.result_preview.lift_pp && (
                            <span className="text-green-600 ml-2">
                              {rule.result_preview.lift_pp}
                            </span>
                          )}
                          {rule.result_preview.warning && (
                            <span className="text-orange-600 ml-2 text-xs">
                              ⚠️ {rule.result_preview.warning}
                            </span>
                          )}
                          {rule.result_preview.reason && (
                            <span className="text-gray-500 ml-2 text-xs">
                              ({rule.result_preview.reason})
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Clarifying Controls */}
        {clarifyingControls && Object.keys(clarifyingControls).length > 0 && (
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Karar Kriterleri</h3>
            <div className="space-y-4">
              {clarifyingControls.decision_goal && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {clarifyingControls.decision_goal.label}
                  </label>
                  <select
                    value={currentGoal}
                    onChange={(e) => setDecisionGoal({ ...decisionGoal, [questionId]: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    {clarifyingControls.decision_goal.options?.map((opt: any) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {clarifyingControls.confidence_threshold && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {clarifyingControls.confidence_threshold.label}: {currentConfidence}%
                  </label>
                  <input
                    type="range"
                    min={clarifyingControls.confidence_threshold.min}
                    max={clarifyingControls.confidence_threshold.max}
                    step={clarifyingControls.confidence_threshold.step}
                    value={currentConfidence}
                    onChange={(e) => setConfidenceThreshold({ ...confidenceThreshold, [questionId]: parseInt(e.target.value) })}
                    className="w-full"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Next Best Questions */}
        {nextBestQuestions && nextBestQuestions.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              Önerilen Takip Soruları
            </h3>
            <p className="text-xs text-gray-600 mb-3">
              Bu sorular cevabı daha ölçülebilir hale getirebilir:
            </p>
            <div className="space-y-2">
              {nextBestQuestions.map((q: string, idx: number) => (
                <button
                  key={idx}
                  onClick={() => handleNextBestQuestion(q)}
                  className="w-full text-left px-3 py-2 text-sm bg-white hover:bg-green-100 border border-green-200 hover:border-green-400 rounded-lg transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
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
            thread.questions.map((question) => {
              // AGGRESSIVE DEBUG - Log EVERY question
              console.log('🚀 RENDERING QUESTION:', {
                id: question.id,
                text: question.question_text,
                mode: question.mode,
                modeType: typeof question.mode,
                hasResult: !!question.result,
                status: question.status
              });
              
              return (
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
                        {/* Decision Proxy Mode */}
                        {(() => {
                          // Debug: Log question data - ALWAYS log
                          console.log('🔍 Question data:', {
                            questionId: question.id,
                            mode: question.mode,
                            modeType: typeof question.mode,
                            modeValue: JSON.stringify(question.mode),
                            hasResult: !!question.result,
                            resultKeys: question.result ? Object.keys(question.result) : [],
                            evidenceJsonKeys: question.result?.evidence_json ? Object.keys(question.result.evidence_json) : [],
                            fullQuestion: question
                          });
                          
                          // Check mode with multiple variations
                          const isDecisionProxy = 
                            question.mode === 'decision_proxy' ||
                            question.mode === 'decision-proxy' ||
                            String(question.mode).toLowerCase() === 'decision_proxy' ||
                            String(question.mode).toLowerCase() === 'decision-proxy';
                          
                          console.log('🔍 Mode check:', {
                            mode: question.mode,
                            isDecisionProxy,
                            check1: question.mode === 'decision_proxy',
                            check2: question.mode === 'decision-proxy',
                            check3: String(question.mode).toLowerCase() === 'decision_proxy'
                          });
                          
                          if (isDecisionProxy) {
                            console.log('✅ Rendering decision_proxy mode');
                            return renderDecisionProxy(question);
                          } else {
                            console.log('❌ Rendering non-decision_proxy mode:', question.mode);
                            
                            // Check for Tier3 disclaimer in structured mode
                            const evidence = question.result.evidence_json || {};
                            const interpretationDisclaimer = evidence.interpretation_disclaimer;
                            const variableTier = evidence.variable_tier;
                            const proxyCopy = evidence.proxy_copy;
                            
                            return (
                          <>
                            {/* Tier3 Disclaimer for Structured Mode */}
                            {interpretationDisclaimer && variableTier === 3 && (
                              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg mb-3">
                                <div className="flex items-start gap-2">
                                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                  <div className="flex-1">
                                    <p className="text-sm font-semibold text-red-900 mb-1">
                                      {proxyCopy?.banner_title || "Using awareness/knowledge as preference proxy"}
                                    </p>
                                    <p className="text-sm text-red-800 font-medium mb-2">
                                      {interpretationDisclaimer}
                                    </p>
                                    {proxyCopy && proxyCopy.what_we_cannot_claim && proxyCopy.what_we_cannot_claim.length > 0 && (
                                      <details className="mt-2">
                                        <summary className="text-xs font-medium cursor-pointer hover:underline mb-1">
                                          What we cannot claim
                                        </summary>
                                        <ul className="list-disc list-inside text-xs space-y-1 mt-1 ml-2">
                                          {proxyCopy.what_we_cannot_claim.map((claim: string, idx: number) => (
                                            <li key={idx} className="text-red-700">
                                              {claim}
                                            </li>
                                          ))}
                                        </ul>
                                      </details>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                            
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
                                  {/* One-line summary at top */}
                                  <div className="mb-3 p-2 bg-gray-100 rounded text-xs font-medium">
                                    {(() => {
                                      const debug = question.result.mapping_debug_json || {};
                                      const mode = debug.mode_selected || debug.reason || 'unknown';
                                      const varCode = debug.chosen_var_code || debug.proxy_var_code || 'N/A';
                                      const confidence = debug.proxy_confidence !== undefined 
                                        ? `${(debug.proxy_confidence * 100).toFixed(0)}%` 
                                        : 'N/A';
                                      return `Mode: ${mode} | Variable: ${varCode} | Confidence: ${confidence}`;
                                    })()}
                                  </div>
                                  <pre className="whitespace-pre-wrap">{JSON.stringify(question.result.mapping_debug_json, null, 2)}</pre>
                                </div>
                              </details>
                            )}
                          </>
                            );
                          }
                        })()}
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
              );
            })
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

