
import React, { useState, useEffect } from 'react';
import { ExperimentSummary } from '../types';
import { listExperiments } from '../services/apiService';

interface ExperimentListProps {
  onSelectExperiment: (id: string) => void;
}

const ExperimentList: React.FC<ExperimentListProps> = ({ onSelectExperiment }) => {
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    listExperiments(100, 0)
      .then(data => {
        setExperiments(data.experiments);
        setTotal(data.total);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = experiments.filter(exp => {
    const q = search.toLowerCase();
    if (!q) return true;
    return (
      exp.taskDescription.toLowerCase().includes(q) ||
      (exp.name || '').toLowerCase().includes(q) ||
      (exp.runnerModel as any)?.model?.toLowerCase().includes(q)
    );
  });

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white/[0.02] border border-white/5 rounded-[32px] p-8 animate-pulse">
            <div className="h-4 bg-white/5 rounded-lg w-3/4 mb-4"></div>
            <div className="h-3 bg-white/5 rounded-lg w-1/2 mb-6"></div>
            <div className="flex gap-4">
              <div className="h-8 bg-white/5 rounded-xl w-20"></div>
              <div className="h-8 bg-white/5 rounded-xl w-20"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/[0.05] border border-red-500/20 rounded-[32px] p-10 text-center">
        <p className="text-red-400 font-bold text-sm">Failed to load experiments</p>
        <p className="text-red-400/60 text-xs mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-black text-gray-500 uppercase tracking-[0.3em] pl-4 border-l-4 border-indigo-500">
            Experiment History
          </h2>
          <p className="text-xs text-gray-600 mt-1 pl-4">{total} experiment{total !== 1 ? 's' : ''}</p>
        </div>
        <input
          type="text"
          placeholder="Search experiments..."
          className="bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-indigo-500/40 w-64 placeholder:text-gray-700"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <div className="h-[400px] flex flex-col items-center justify-center text-center space-y-6 opacity-40 border-4 border-dashed border-white/[0.02] rounded-[60px]">
          <div className="w-20 h-20 bg-[#0a0c12] rounded-[2rem] flex items-center justify-center border border-white/10">
            <svg className="w-10 h-10 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-black text-white/50">No Experiments Found</h3>
            <p className="text-sm text-gray-500 mt-2">
              {search ? 'Try a different search term.' : 'Run an optimization to see experiments here.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filtered.map(exp => (
            <button
              key={exp.id}
              onClick={() => onSelectExperiment(exp.id)}
              className="text-left bg-[#0a0c12]/80 border border-white/5 rounded-[32px] p-8 hover:border-indigo-500/20 transition-all duration-300 group"
            >
              <div className="flex justify-between items-start mb-4">
                <p className="text-sm font-bold text-gray-200 leading-relaxed line-clamp-2 group-hover:text-indigo-300 transition-colors">
                  {exp.taskDescription}
                </p>
                {exp.isComplete ? (
                  <span className="flex-shrink-0 ml-3 px-3 py-1 rounded-xl bg-green-500/10 text-green-400 text-[9px] font-black uppercase border border-green-500/20">
                    Complete
                  </span>
                ) : (
                  <span className="flex-shrink-0 ml-3 px-3 py-1 rounded-xl bg-yellow-500/10 text-yellow-400 text-[9px] font-black uppercase border border-yellow-500/20">
                    In Progress
                  </span>
                )}
              </div>

              <p className="text-[10px] font-mono text-gray-600 mb-6 truncate">
                {(exp.runnerModel as any)?.model || 'Unknown model'}
              </p>

              <div className="flex items-center gap-4 flex-wrap">
                <span className="px-3 py-1.5 rounded-xl bg-indigo-500/10 text-indigo-400 text-[10px] font-black border border-indigo-500/20">
                  {exp.iterationCount} iteration{exp.iterationCount !== 1 ? 's' : ''}
                </span>
                {exp.bestScore != null && (
                  <span className={`px-3 py-1.5 rounded-xl text-[10px] font-black border ${
                    exp.bestScore >= 90 ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                    exp.bestScore >= 60 ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                    'bg-red-500/10 text-red-400 border-red-500/20'
                  }`}>
                    Best: {exp.bestScore.toFixed(1)}%
                  </span>
                )}
                <span className="px-3 py-1.5 rounded-xl bg-white/[0.03] text-gray-500 text-[10px] font-bold border border-white/5">
                  {exp.datasetSize} row{exp.datasetSize !== 1 ? 's' : ''}
                </span>
                <span className="text-[10px] text-gray-600 ml-auto">
                  {new Date(exp.createdAt).toLocaleDateString()}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ExperimentList;
