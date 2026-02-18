
import React from 'react';
import { IterationStep } from '../types';

// Helper to calculate simple line-based diff
const getLineDiff = (oldText: string, newText: string) => {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  return {
    removed: oldLines.filter(line => !newLines.includes(line) && line.trim().length > 0),
    added: newLines.filter(line => !oldLines.includes(line) && line.trim().length > 0)
  };
};

interface IterationCardProps {
  step: IterationStep;
  prevPrompt: string | null;
  scoreDelta: number;
  showRowDetails?: boolean;
}

const IterationCard: React.FC<IterationCardProps> = ({ step, prevPrompt, scoreDelta, showRowDetails = false }) => {
  const diff = prevPrompt ? getLineDiff(prevPrompt, step.prompt) : null;

  return (
    <div className="bg-[#0a0c12]/80 border border-white/5 rounded-[40px] overflow-hidden shadow-2xl backdrop-blur-xl group hover:border-indigo-500/20 transition-all duration-500">
      <div className="px-10 py-8 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
        <div className="flex items-center gap-6">
          <span className="px-5 py-2 rounded-2xl bg-indigo-500/10 text-indigo-400 font-black text-xs border border-indigo-500/20 tracking-tighter">
            CYCLE {step.iteration}
          </span>
          <div className="flex flex-col">
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Performance Bench</span>
            <div className="flex items-center gap-3">
              <span className="text-4xl font-black text-white tabular-nums">{step.averageScore.toFixed(1)}%</span>
              {scoreDelta !== 0 && (
                <span className={`text-sm font-bold flex items-center gap-1 ${scoreDelta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {scoreDelta > 0 ? '\u25B2' : '\u25BC'} {Math.abs(scoreDelta).toFixed(1)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="p-10 space-y-10">
        {/* THE DIFF SCREEN / SECTION */}
        <div className="grid grid-cols-1 gap-8">
          <div className="space-y-4">
            <h4 className="text-[10px] font-black text-indigo-400/80 uppercase tracking-widest">Modified Logic Delta</h4>
            <div className="bg-black/40 rounded-3xl border border-white/5 overflow-hidden">
              <div className="p-6 font-mono text-[13px] leading-relaxed space-y-2">
                {!diff && (
                  <div className="text-gray-500 italic">Baseline Prompt Initialized</div>
                )}
                {diff && diff.removed.length === 0 && diff.added.length === 0 && (
                  <div className="text-gray-500 italic">No structural changes detected</div>
                )}
                {diff && (
                  <>
                    {diff.removed.map((l, li) => (
                      <div key={li} className="text-red-400/60 flex gap-4">
                        <span className="opacity-40">-</span>
                        <span className="line-through">{l}</span>
                      </div>
                    ))}
                    {diff.added.map((l, li) => (
                      <div key={li} className="text-green-400 flex gap-4">
                        <span className="opacity-40">+</span>
                        <span>{l}</span>
                      </div>
                    ))}
                    {step.prompt.split('\n').filter(line => !diff.added.includes(line) && !diff.removed.includes(line)).slice(0, 2).map((l, li) => (
                      <div key={li} className="text-gray-600 opacity-50 flex gap-4 italic text-[11px]">
                        <span className="opacity-40">...</span>
                        <span>{l.slice(0, 100)}...</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-indigo-500/[0.03] border border-indigo-500/10 p-8 rounded-[32px] flex flex-col gap-4 shadow-xl">
              <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-3">Refinement Logic</p>
                <p className="text-sm text-indigo-100/80 leading-relaxed italic font-medium">
                  {step.refinementFeedback.split('\n\nImpact Analysis:')[0]}
                </p>
              </div>
            </div>

            <div className="bg-cyan-500/[0.03] border border-cyan-500/10 p-8 rounded-[32px] flex flex-col gap-4 shadow-xl">
              <div className="w-10 h-10 rounded-2xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 mb-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-black text-cyan-400 uppercase tracking-widest mb-3">Lift Impact Analysis</p>
                <p className="text-sm text-cyan-100/80 leading-relaxed font-medium">
                  {step.refinementFeedback.split('\n\nImpact Analysis:')[1] || "Initializing baseline benchmarks for propagation."}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Per-row details (used in history view) */}
        {showRowDetails && step.results.length > 0 && (
          <details className="group">
            <summary className="text-[10px] font-black text-gray-500 uppercase tracking-widest cursor-pointer hover:text-indigo-400 transition-colors list-none flex items-center gap-2">
              <span className="group-open:rotate-90 transition-transform">{'\u25B6'}</span>
              Per-Row Results ({step.results.length} rows)
            </summary>
            <div className="mt-4 space-y-3">
              {step.results.map((r, ri) => (
                <div key={ri} className="bg-black/30 border border-white/5 rounded-2xl p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-bold text-gray-500 uppercase">Row {ri + 1}</span>
                    <span className={`text-sm font-black tabular-nums ${r.averageScore >= 90 ? 'text-green-400' : r.averageScore >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {r.averageScore.toFixed(1)}%
                    </span>
                  </div>
                  {r.actualOutput && (
                    <p className="text-xs text-gray-400 font-mono line-clamp-2">{r.actualOutput}</p>
                  )}
                  {r.combinedFeedback && (
                    <p className="text-[11px] text-gray-500 italic line-clamp-3">{r.combinedFeedback}</p>
                  )}
                </div>
              ))}
            </div>
          </details>
        )}

        <div className="pt-4">
          <details className="group">
            <summary className="text-[10px] font-black text-gray-500 uppercase tracking-widest cursor-pointer hover:text-indigo-400 transition-colors list-none flex items-center gap-2">
              <span className="group-open:rotate-90 transition-transform">{'\u25B6'}</span>
              Full Resultant Prompt
            </summary>
            <div className="mt-4 relative group/code">
              <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-cyan-500/20 rounded-3xl blur-xl opacity-0 group-hover/code:opacity-30 transition duration-1000"></div>
              <div className="relative bg-black/60 p-8 rounded-[32px] border border-white/5 font-mono text-[13px] text-gray-300 leading-relaxed whitespace-pre-wrap max-h-[400px] overflow-y-auto custom-scrollbar">
                {step.prompt}
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default IterationCard;
