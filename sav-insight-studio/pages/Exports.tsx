import React, { useEffect, useState } from 'react';
import { apiService } from '../services/apiService';
import { FileSpreadsheet, FileJson, FileText, Download, FileCode, CheckCircle, Loader2, Eye } from 'lucide-react';
import { DatasetMeta, SmartFilter } from '../types';
import nativeLogo from '../native-logo.png';

const Exports: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState<Set<string>>(new Set());
  const [smartFilters, setSmartFilters] = useState<SmartFilter[]>([]);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (stored) {
      const parsedMeta = JSON.parse(stored);
      setMeta(parsedMeta);
      
      // Load smart filters from database
      const loadFilters = async () => {
        try {
          const result = await apiService.getSmartFilters(parsedMeta.id);
          if (result && result.filters && result.filters.length > 0) {
            setSmartFilters(result.filters);
            // Set active filters based on isApplied flag
            const active = result.filters
              .filter((f: any) => f.isApplied !== false)
              .map((f: any) => f.id);
            setActiveFilters(active);
          } else {
            // Fallback: try localStorage (migration support)
            const savedFilters = localStorage.getItem(`smartFilters_${parsedMeta.id}`);
            if (savedFilters) {
              try {
                const parsed = JSON.parse(savedFilters);
                setSmartFilters(parsed.filters || []);
              } catch (e) {
                console.error('Failed to parse smart filters from localStorage:', e);
              }
            }
            
            const savedActiveFilters = localStorage.getItem(`activeFilters_${parsedMeta.id}`);
            if (savedActiveFilters) {
              try {
                setActiveFilters(JSON.parse(savedActiveFilters));
              } catch (e) {
                console.error('Failed to parse active filters from localStorage:', e);
              }
            }
          }
        } catch (e) {
          console.error('Failed to load smart filters from database:', e);
          // Fallback to localStorage
          const savedFilters = localStorage.getItem(`smartFilters_${parsedMeta.id}`);
          if (savedFilters) {
            try {
              const parsed = JSON.parse(savedFilters);
              setSmartFilters(parsed.filters || []);
            } catch (parseError) {
              console.error('Failed to parse smart filters:', parseError);
            }
          }
          
          const savedActiveFilters = localStorage.getItem(`activeFilters_${parsedMeta.id}`);
          if (savedActiveFilters) {
            try {
              setActiveFilters(JSON.parse(savedActiveFilters));
            } catch (parseError) {
              console.error('Failed to parse active filters:', parseError);
            }
          }
        }
      };
      
      loadFilters();
    }
  }, []);

  const handleDownload = async (type: 'excel' | 'json' | 'report' | 'summary') => {
    if (!meta) return;
    
    setDownloading(type);
    try {
      await apiService.downloadExport(meta.id, type);
      setDownloaded(prev => new Set([...prev, type]));
    } catch (err) {
      console.error('Download error:', err);
      alert('Download failed. Is the backend running?');
    } finally {
      setDownloading(null);
    }
  };

  const generateHTMLReport = () => {
    if (!meta) return '';
    
    const report = meta.qualityReport;
    const appliedFilters = smartFilters.filter(f => activeFilters.includes(f.id));
    const currentDate = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    // Convert logo to base64 for embedding
    const logoBase64 = nativeLogo;

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report - ${meta.filename}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: #f8fafc;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .logo {
            max-width: 180px;
            height: auto;
            margin-bottom: 20px;
            filter: brightness(0) invert(1);
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .header .subtitle {
            font-size: 16px;
            opacity: 0.9;
        }
        
        .header .date {
            font-size: 13px;
            opacity: 0.7;
            margin-top: 16px;
        }
        
        /* Content */
        .content {
            padding: 40px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section-title {
            font-size: 20px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        /* Executive Summary */
        .executive-summary {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-top: 20px;
        }
        
        .summary-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .summary-card .value {
            font-size: 32px;
            font-weight: 700;
            color: #1e40af;
        }
        
        .summary-card .label {
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }
        
        /* Status Badge */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }
        
        .status-green {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-yellow {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-red {
            background: #fee2e2;
            color: #991b1b;
        }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        
        .metric-card {
            background: #f9fafb;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e5e7eb;
        }
        
        .metric-card h4 {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 8px;
        }
        
        .metric-card .value {
            font-size: 24px;
            font-weight: 700;
            color: #111827;
        }
        
        .metric-card .bar {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            margin-top: 12px;
            overflow: hidden;
        }
        
        .metric-card .bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        
        .bar-green { background: #22c55e; }
        .bar-yellow { background: #f59e0b; }
        .bar-red { background: #ef4444; }
        .bar-blue { background: #3b82f6; }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th {
            background: #f3f4f6;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }
        
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
        }
        
        tr:hover {
            background: #f9fafb;
        }
        
        .text-right {
            text-align: right;
        }
        
        .text-center {
            text-align: center;
        }
        
        /* Variable Quality */
        .quality-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .quality-good { background: #22c55e; }
        .quality-medium { background: #f59e0b; }
        .quality-low { background: #ef4444; }
        
        /* Smart Filters Section */
        .filters-section {
            background: #faf5ff;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #e9d5ff;
        }
        
        .filter-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-top: 12px;
            border: 1px solid #e5e7eb;
        }
        
        .filter-card h4 {
            font-weight: 600;
            color: #7c3aed;
            margin-bottom: 8px;
        }
        
        .filter-card p {
            font-size: 13px;
            color: #6b7280;
        }
        
        .filter-vars {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        
        .filter-var {
            background: #f3f4f6;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            color: #374151;
        }
        
        .no-filters {
            text-align: center;
            padding: 30px;
            color: #9ca3af;
        }
        
        /* Issues & Recommendations */
        .issues-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        
        .issue-card {
            border-radius: 8px;
            padding: 20px;
        }
        
        .issue-card.critical {
            background: #fef2f2;
            border: 1px solid #fecaca;
        }
        
        .issue-card.warning {
            background: #fffbeb;
            border: 1px solid #fde68a;
        }
        
        .issue-card.recommendation {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
        }
        
        .issue-card h4 {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        
        .issue-card.critical h4 { color: #991b1b; }
        .issue-card.warning h4 { color: #92400e; }
        .issue-card.recommendation h4 { color: #1e40af; }
        
        .issue-list {
            list-style: none;
        }
        
        .issue-list li {
            font-size: 13px;
            padding: 6px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        
        .issue-list li:last-child {
            border-bottom: none;
        }
        
        /* Footer */
        .footer {
            background: #1f2937;
            color: white;
            padding: 30px 40px;
            text-align: center;
        }
        
        .footer-logo {
            max-width: 120px;
            height: auto;
            margin-bottom: 16px;
            filter: brightness(0) invert(1);
        }
        
        .footer p {
            font-size: 13px;
            opacity: 0.7;
        }
        
        .footer .powered {
            margin-top: 12px;
            font-size: 11px;
            opacity: 0.5;
        }
        
        /* Print Styles */
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <img src="${logoBase64}" alt="Native AI" class="logo">
            <h1>Data Analysis Report</h1>
            <div class="subtitle">${meta.filename}</div>
            <div class="date">Generated on ${currentDate}</div>
        </div>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="executive-summary">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="font-size: 18px; font-weight: 700; color: #1e40af;">Executive Summary</h2>
                        <p style="color: #6b7280; margin-top: 4px;">Overview of your dataset analysis</p>
                    </div>
                    <div class="status-badge status-${report?.digital_twin_readiness || 'yellow'}">
                        ${report?.digital_twin_readiness === 'green' ? '✓ Digital Twin Ready' : 
                          report?.digital_twin_readiness === 'yellow' ? '⚠ Needs Attention' : 
                          '✗ Not Ready'}
                    </div>
                </div>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="value">${meta.nRows.toLocaleString()}</div>
                        <div class="label">Total Respondents</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">${meta.nCols.toLocaleString()}</div>
                        <div class="label">Variables</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">${report?.overall_score?.toFixed(0) || 'N/A'}%</div>
                        <div class="label">Quality Score</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">${report?.completeness_score?.toFixed(0) || 'N/A'}%</div>
                        <div class="label">Completeness</div>
                    </div>
                </div>
            </div>
            
            <!-- Quality Metrics -->
            <div class="section">
                <h3 class="section-title">📊 Quality Metrics</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Completeness Score</h4>
                        <div class="value">${report?.completeness_score?.toFixed(1) || 'N/A'}%</div>
                        <div class="bar">
                            <div class="bar-fill bar-${(report?.completeness_score || 0) >= 80 ? 'green' : (report?.completeness_score || 0) >= 60 ? 'yellow' : 'red'}" 
                                 style="width: ${report?.completeness_score || 0}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <h4>Validity Score</h4>
                        <div class="value">${report?.validity_score?.toFixed(1) || 'N/A'}%</div>
                        <div class="bar">
                            <div class="bar-fill bar-${(report?.validity_score || 0) >= 80 ? 'green' : (report?.validity_score || 0) >= 60 ? 'yellow' : 'red'}" 
                                 style="width: ${report?.validity_score || 0}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <h4>Consistency Score</h4>
                        <div class="value">${report?.consistency_score?.toFixed(1) || 'N/A'}%</div>
                        <div class="bar">
                            <div class="bar-fill bar-${(report?.consistency_score || 0) >= 80 ? 'green' : (report?.consistency_score || 0) >= 60 ? 'yellow' : 'red'}" 
                                 style="width: ${report?.consistency_score || 0}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <h4>Transformation Readiness</h4>
                        <div class="value">${report?.transformation_score?.toFixed(1) || 'N/A'}%</div>
                        <div class="bar">
                            <div class="bar-fill bar-blue" style="width: ${report?.transformation_score || 0}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Response Statistics -->
            <div class="section">
                <h3 class="section-title">👥 Response Statistics</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Complete Responses</h4>
                        <div class="value">${report?.complete_responses?.toLocaleString() || 'N/A'}</div>
                        <p style="font-size: 13px; color: #6b7280; margin-top: 8px;">
                            ${((report?.complete_responses || 0) / meta.nRows * 100).toFixed(1)}% of total respondents
                        </p>
                    </div>
                    <div class="metric-card">
                        <h4>Partial Responses</h4>
                        <div class="value">${report?.partial_responses?.toLocaleString() || 'N/A'}</div>
                        <p style="font-size: 13px; color: #6b7280; margin-top: 8px;">
                            ${((report?.partial_responses || 0) / meta.nRows * 100).toFixed(1)}% of total respondents
                        </p>
                    </div>
                    <div class="metric-card">
                        <h4>Dropout Rate</h4>
                        <div class="value" style="color: ${(report?.dropout_rate || 0) > 20 ? '#ef4444' : '#22c55e'}">
                            ${report?.dropout_rate?.toFixed(1) || 'N/A'}%
                        </div>
                        <p style="font-size: 13px; color: #6b7280; margin-top: 8px;">
                            ${(report?.dropout_rate || 0) <= 10 ? 'Excellent retention' : 
                              (report?.dropout_rate || 0) <= 20 ? 'Acceptable retention' : 'High dropout'}
                        </p>
                    </div>
                    <div class="metric-card">
                        <h4>Variable Quality Distribution</h4>
                        <div style="display: flex; gap: 16px; margin-top: 12px;">
                            <div style="text-align: center;">
                                <div style="font-size: 20px; font-weight: 700; color: #22c55e;">${report?.high_quality_vars || 0}</div>
                                <div style="font-size: 11px; color: #6b7280;">High</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 20px; font-weight: 700; color: #f59e0b;">${report?.medium_quality_vars || 0}</div>
                                <div style="font-size: 11px; color: #6b7280;">Medium</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${report?.low_quality_vars || 0}</div>
                                <div style="font-size: 11px; color: #6b7280;">Low</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Smart Filters -->
            <div class="section">
                <h3 class="section-title">🎯 Smart Filters Analysis</h3>
                <div class="filters-section">
                    ${appliedFilters.length > 0 ? `
                        <p style="color: #7c3aed; font-weight: 600; margin-bottom: 16px;">
                            ${appliedFilters.length} Smart Filter${appliedFilters.length > 1 ? 's' : ''} Applied
                        </p>
                        ${appliedFilters.map(filter => `
                            <div class="filter-card">
                                <h4>${filter.title}</h4>
                                <p>${filter.rationale}</p>
                                <div class="filter-vars">
                                    ${filter.sourceVars.map(v => `<span class="filter-var">${v}</span>`).join('')}
                                </div>
                                <div style="margin-top: 12px; font-size: 12px; color: #9ca3af;">
                                    Suitability Score: <strong style="color: #22c55e;">${filter.suitabilityScore}/10</strong>
                                </div>
                            </div>
                        `).join('')}
                    ` : `
                        <div class="no-filters">
                            <p style="font-size: 16px; margin-bottom: 8px;">No Smart Filters Applied</p>
                            <p style="font-size: 13px;">Smart filters can be generated using AI to identify optimal segmentation variables for your dashboard.</p>
                        </div>
                    `}
                </div>
            </div>
            
            <!-- Issues & Recommendations -->
            ${(report?.critical_issues?.length || report?.warnings?.length || report?.recommendations?.length) ? `
            <div class="section">
                <h3 class="section-title">⚠️ Issues & Recommendations</h3>
                <div class="issues-grid">
                    <div class="issue-card critical">
                        <h4>🚨 Critical Issues (${report?.critical_issues?.length || 0})</h4>
                        ${report?.critical_issues?.length ? `
                            <ul class="issue-list">
                                ${report.critical_issues.map(issue => `<li>• ${issue}</li>`).join('')}
                            </ul>
                        ` : '<p style="font-size: 13px; color: #6b7280;">No critical issues found</p>'}
                    </div>
                    <div class="issue-card warning">
                        <h4>⚠️ Warnings (${report?.warnings?.length || 0})</h4>
                        ${report?.warnings?.length ? `
                            <ul class="issue-list">
                                ${report.warnings.map(warning => `<li>• ${warning}</li>`).join('')}
                            </ul>
                        ` : '<p style="font-size: 13px; color: #6b7280;">No warnings</p>'}
                    </div>
                    <div class="issue-card recommendation">
                        <h4>💡 Recommendations (${report?.recommendations?.length || 0})</h4>
                        ${report?.recommendations?.length ? `
                            <ul class="issue-list">
                                ${report.recommendations.map(rec => `<li>• ${rec}</li>`).join('')}
                            </ul>
                        ` : '<p style="font-size: 13px; color: #6b7280;">No recommendations</p>'}
                    </div>
                </div>
            </div>
            ` : ''}
            
            <!-- Variable Quality Table -->
            <div class="section">
                <h3 class="section-title">📋 Variable Quality Analysis</h3>
                <p style="color: #6b7280; margin-bottom: 16px; font-size: 14px;">
                    Showing variables sorted by completeness (lowest first)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>Variable</th>
                            <th>Label</th>
                            <th class="text-center">Completeness</th>
                            <th class="text-center">Status</th>
                            <th>Issues</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(report?.variable_quality || [])
                            .sort((a, b) => a.completeness - b.completeness)
                            .slice(0, 30)
                            .map(v => `
                                <tr>
                                    <td><code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 12px;">${v.code}</code></td>
                                    <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${v.label}</td>
                                    <td class="text-center">
                                        <span style="font-weight: 600; color: ${v.completeness >= 90 ? '#22c55e' : v.completeness >= 70 ? '#f59e0b' : '#ef4444'}">
                                            ${v.completeness.toFixed(0)}%
                                        </span>
                                    </td>
                                    <td class="text-center">
                                        <span class="quality-indicator quality-${v.status === 'green' ? 'good' : v.status === 'yellow' ? 'medium' : 'low'}"></span>
                                        ${v.status === 'green' ? 'Good' : v.status === 'yellow' ? 'Medium' : 'Low'}
                                    </td>
                                    <td style="font-size: 12px; color: #6b7280;">${v.issues.length > 0 ? v.issues.join('; ') : '-'}</td>
                                </tr>
                            `).join('')}
                    </tbody>
                </table>
                ${(report?.variable_quality?.length || 0) > 30 ? `
                    <p style="text-align: center; color: #9ca3af; margin-top: 16px; font-size: 13px;">
                        Showing 30 of ${report?.variable_quality?.length} variables
                    </p>
                ` : ''}
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <img src="${logoBase64}" alt="Native AI" class="footer-logo">
            <p>This report was automatically generated by SAV Insight Studio</p>
            <p class="powered">Powered by Native AI • ${currentDate}</p>
        </div>
    </div>
</body>
</html>`;
  };

  const downloadHTMLReport = () => {
    if (!meta) return;
    
    setDownloading('html');
    
    try {
      const htmlContent = generateHTMLReport();
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${meta.filename.replace('.sav', '')}_analysis_report.html`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setDownloaded(prev => new Set([...prev, 'html']));
    } catch (err) {
      console.error('HTML export error:', err);
      alert('Failed to generate HTML report');
    } finally {
      setDownloading(null);
    }
  };

  const previewHTMLReport = () => {
    const htmlContent = generateHTMLReport();
    const newWindow = window.open('', '_blank');
    if (newWindow) {
      newWindow.document.write(htmlContent);
      newWindow.document.close();
    }
  };

  if (!meta) return null;

  const appliedFiltersCount = smartFilters.filter(f => activeFilters.includes(f.id)).length;

  const Option = ({ icon, title, desc, type, highlight, onDownload, onPreview }: { 
    icon: React.ReactNode; 
    title: string; 
    desc: string; 
    type: string;
    highlight?: boolean;
    onDownload: () => void;
    onPreview?: () => void;
  }) => (
    <div className={`bg-white p-6 rounded-2xl border-2 transition-all group ${
      highlight 
        ? 'border-blue-400 shadow-lg shadow-blue-100' 
        : 'border-gray-200 hover:border-blue-400 hover:shadow-lg'
    }`}>
      {highlight && (
        <div className="text-xs font-bold text-blue-600 mb-3 uppercase tracking-wider">
          ✨ Recommended
        </div>
      )}
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-colors ${
        highlight 
          ? 'bg-blue-600 text-white' 
          : 'bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white'
      }`}>
        {icon}
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6 text-sm leading-relaxed">{desc}</p>
      <div className="flex gap-2">
        {onPreview && (
          <button
            onClick={onPreview}
            className={`flex-1 font-medium py-3 rounded-xl flex items-center justify-center space-x-2 transition-all ${
              highlight
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Eye size={18} />
            <span>View Report</span>
          </button>
        )}
        <button 
          onClick={onDownload}
          disabled={downloading === type}
          className={`${onPreview ? 'px-4' : 'flex-1'} font-medium py-3 rounded-xl flex items-center justify-center space-x-2 transition-all ${
            downloaded.has(type)
              ? 'bg-green-100 text-green-700 border border-green-300'
              : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
          title="Download"
        >
          {downloading === type ? (
            <Loader2 size={18} className="animate-spin" />
          ) : downloaded.has(type) ? (
            <CheckCircle size={18} />
          ) : (
            <Download size={18} />
          )}
          {!onPreview && (
            <span>{downloading === type ? 'Generating...' : downloaded.has(type) ? 'Downloaded' : 'Download'}</span>
          )}
        </button>
      </div>
    </div>
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Export</h1>
      <p className="text-gray-500 mb-8">Download your dataset and analyses in various formats.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Option 
          icon={<FileCode />} 
          title="Professional Report (HTML)" 
          desc={`Beautiful, shareable HTML report with executive summary, quality metrics, ${appliedFiltersCount > 0 ? `${appliedFiltersCount} applied smart filters` : 'smart filter status'}, and detailed variable analysis. Ready for client presentations.`}
          type="html"
          highlight={true}
          onDownload={downloadHTMLReport}
          onPreview={previewHTMLReport}
        />
        <Option 
          icon={<FileSpreadsheet />} 
          title="Data (Excel)" 
          desc="Excel file containing raw data and labeled data sheets. Ideal for manual analysis and further processing." 
          type="excel"
          onDownload={() => handleDownload('excel')}
        />
        <Option 
          icon={<FileJson />} 
          title="JSON Metadata" 
          desc="JSON format containing all variable metadata, value labels, types, and quality scores for integration." 
          type="json"
          onDownload={() => handleDownload('json')}
        />
      </div>

      {/* Quick Stats */}
      <div className="mt-8 p-6 bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl border border-gray-100">
        <h3 className="font-bold text-gray-900 mb-4">Dataset Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Filename:</span>
            <p className="font-medium text-gray-900">{meta.filename}</p>
          </div>
          <div>
            <span className="text-gray-500">Respondents:</span>
            <p className="font-medium text-gray-900">{meta.nRows.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Variables:</span>
            <p className="font-medium text-gray-900">{meta.nCols.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Smart Filters:</span>
            <p className={`font-medium ${appliedFiltersCount > 0 ? 'text-purple-600' : 'text-gray-400'}`}>
              {appliedFiltersCount > 0 ? `${appliedFiltersCount} Applied` : 'None'}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Digital Twin:</span>
            <p className={`font-medium ${
              meta.digitalTwinReadiness === 'green' ? 'text-green-600' :
              meta.digitalTwinReadiness === 'yellow' ? 'text-amber-600' : 'text-red-600'
            }`}>
              {meta.digitalTwinReadiness === 'green' ? '✅ Ready' :
               meta.digitalTwinReadiness === 'yellow' ? '⚠️ Caution' : '❌ Not Ready'}
            </p>
          </div>
        </div>
      </div>

    </div>
  );
};

export default Exports;
