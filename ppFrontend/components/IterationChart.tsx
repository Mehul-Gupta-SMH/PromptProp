
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { IterationStep } from '../types';

interface IterationChartProps {
  history: IterationStep[];
}

const IterationChart: React.FC<IterationChartProps> = ({ history }) => {
  const data = history.map(h => ({
    iteration: h.iteration,
    score: h.averageScore
  }));

  if (data.length < 2) return null;

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 h-64 mb-6">
      <h3 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Performance Lift</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="iteration" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis domain={[0, 100]} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '8px' }}
            itemStyle={{ color: '#60a5fa' }}
          />
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#3b82f6" 
            strokeWidth={3} 
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default IterationChart;
