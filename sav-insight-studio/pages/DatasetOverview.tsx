import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DatasetMeta } from '../types';
import { Users, LayoutGrid, CheckCircle, AlertTriangle } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { COLORS } from '../constants';

const DatasetOverview: React.FC = () => {
  const [meta, setMeta] = useState<DatasetMeta | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const stored = localStorage.getItem('currentDatasetMeta');
    if (!stored) {
      navigate('/');
      return;
    }
    setMeta(JSON.parse(stored));
  }, [navigate]);

  if (!meta) return null;

  // Derive stats
  const typeCounts = meta.variables.reduce((acc, v) => {
    acc[v.type] = (acc[v.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const typeData = Object.entries(typeCounts).map(([name, value]) => ({ name, value }));
  
  const avgResponseRate = Math.round(
    meta.variables.reduce((sum, v) => sum + v.responseRate, 0) / meta.variables.length
  );

  const missingHeavyVars = meta.variables
    .filter(v => v.responseRate < 80)
    .sort((a, b) => a.responseRate - b.responseRate)
    .slice(0, 5);

  const StatCard = ({ title, value, icon, color }: any) => (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-gray-900">{value}</h3>
      </div>
      <div className={`p-3 rounded-xl ${color}`}>
        {icon}
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{meta.filename}</h1>
        <p className="text-gray-500">Dataset Overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Respondents" 
          value={meta.nRows.toLocaleString()} 
          icon={<Users size={24} className="text-blue-600" />} 
          color="bg-blue-50"
        />
        <StatCard 
          title="Total Variables" 
          value={meta.nCols.toLocaleString()} 
          icon={<LayoutGrid size={24} className="text-purple-600" />} 
          color="bg-purple-50"
        />
        <StatCard 
          title="Avg. Completion" 
          value={`${avgResponseRate}%`} 
          icon={<CheckCircle size={24} className="text-green-600" />} 
          color="bg-green-50"
        />
        <StatCard 
          title="High Missing Vars" 
          value={missingHeavyVars.length} 
          icon={<AlertTriangle size={24} className="text-amber-600" />} 
          color="bg-amber-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Variable Types Distribution</h3>
          <div className="h-64 w-full min-w-0" style={{ minHeight: '256px' }}>
            <ResponsiveContainer width="100%" height="100%" minHeight={256} aspect={undefined}>
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {typeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % 8]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-4">
             {typeData.map((entry, index) => (
                <div key={entry.name} className="flex items-center text-sm">
                  <span className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: Object.values(COLORS)[index % 8] }}></span>
                  <span className="text-gray-600 capitalize">{entry.name.replace('_', ' ')}: {entry.value}</span>
                </div>
             ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Lowest Completion Rates</h3>
          <div className="h-64 w-full min-w-0" style={{ minHeight: '256px' }}>
            <ResponsiveContainer width="100%" height="100%" minHeight={256} aspect={undefined}>
               <BarChart data={missingHeavyVars} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis dataKey="code" type="category" width={60} tick={{fontSize: 12}} />
                  <Tooltip cursor={{fill: 'transparent'}} />
                  <Bar dataKey="responseRate" fill={COLORS.danger} radius={[0, 4, 4, 0]} barSize={20} />
               </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-400 mt-4 text-center">Variables with highest missing value percentage.</p>
        </div>
      </div>
    </div>
  );
};

export default DatasetOverview;