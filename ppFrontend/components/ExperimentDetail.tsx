
import React, { useState, useEffect } from 'react';
import { ExperimentDetail as ExperimentDetailType, IterationStep, TestCaseResult } from '../types';
import { getExperimentDetail } from '../services/apiService';
import IterationChart from './IterationChart';
import IterationCard from './IterationCard';

interface ExperimentDetailProps {
  experimentId: string;
  onBack: () => void;
  onLoadIntoOptimizer: (experiment: ExperimentDetailType) => void;
}

/** Convert backend prompt versions into IterationStep[] for chart/card reuse */
const toIterationSteps = (experiment: ExperimentDetailType): IterationStep[] => {
  return experiment.promptVersions.map(pv => {
    const results: TestCaseResult[] = pv.results.map(ir => ({
      rowId: ir.datasetRowId,
      actualOutput: ir.actualOutput,
      scores: ir.juryEvaluations.map(je => ({
        juryName: je.juryName,
        score: je.score,
        reasoning: je.reasoning,
      })),
      averageScore: ir.averageScore ?? 0,
      combinedFeedback: ir.combinedFeedback || '',
    }));

    return {
      iteration: pv.iterationNumber,
      prompt: pv.promptText,
      averageScore: pv.averageScore ?? 0,
      results,
      refinementFeedback: pv.refinementFeedback || (pv.iterationNumber === 1 ? 'Baseline established.' : ''),
    };
  });
};

const ExperimentDetailView: React.FC<ExperimentDetailProps> = ({ experimentId, onBack, onLoadIntoOptimizer }) => {
  const [experiment, setExperiment] = useState<ExperimentDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getExperimentDetail(experimentId)
      .then(data => {
        setExperiment(data);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [experimentId]);

  if (loading) {
    return (
      <div className="space-y-8 animate-pulse">
        <div className="h-6 bg-white/5 rounded-lg w-48"></div>
        <div className="h-64 bg-white/[0.02] border border-white/5 rounded-[32px]"></div>
        <div className="h-96 bg-white/[0.02] border border-white/5 rounded-[40px]"></div>
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className="space-y-6">
        <button onClick={onBack} className="text-xs font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-wider">
          &larr; Back to List
        </button>
        <div className="bg-red-500/[0.05] border border-red-500/20 rounded-[32px] p-10 text-center">
          <p className="text-red-400 font-bold text-sm">Failed to load experiment</p>
          <p className="text-red-400/60 text-xs mt-2">{error}</p>
        </div>
      </div>
    );
  }

  const steps = toIterationSteps(experiment);

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div className="space-y-3">
          <button onClick={onBack} className="text-xs font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-wider transition-colors">
            &larr; Back to List
          </button>
          <h2 className="text-lg font-black text-white leading-relaxed">{experiment.taskDescription}</h2>
          <div className="flex items-center gap-4 flex-wrap">
            <span className="px-3 py-1.5 rounded-xl bg-white/[0.03] text-gray-400 text-[10px] font-mono border border-white/5">
              {(experiment.runnerModel as any)?.model || 'Unknown'}
            </span>
            <span className="px-3 py-1.5 rounded-xl bg-indigo-500/10 text-indigo-400 text-[10px] font-black border border-indigo-500/20">
              {experiment.promptVersions.length} iteration{experiment.promptVersions.length !== 1 ? 's' : ''}
            </span>
            <span className="px-3 py-1.5 rounded-xl bg-white/[0.03] text-gray-500 text-[10px] font-bold border border-white/5">
              {experiment.datasetRows.length} row{experiment.datasetRows.length !== 1 ? 's' : ''}
            </span>
            {experiment.juryMembers.length > 0 && (
              <span className="px-3 py-1.5 rounded-xl bg-purple-500/10 text-purple-400 text-[10px] font-bold border border-purple-500/20">
                {experiment.juryMembers.map(j => j.name).join(', ')}
              </span>
            )}
            <span className="text-[10px] text-gray-600">
              {new Date(experiment.createdAt).toLocaleString()}
            </span>
            {experiment.isComplete ? (
              <span className="px-3 py-1 rounded-xl bg-green-500/10 text-green-400 text-[9px] font-black uppercase border border-green-500/20">
                Complete
              </span>
            ) : (
              <span className="px-3 py-1 rounded-xl bg-yellow-500/10 text-yellow-400 text-[9px] font-black uppercase border border-yellow-500/20">
                In Progress
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => onLoadIntoOptimizer(experiment)}
          className="flex-shrink-0 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-xs font-black uppercase tracking-wider transition-all shadow-lg shadow-indigo-900/40"
        >
          Load into Optimizer
        </button>
      </div>

      {/* Chart */}
      {steps.length >= 2 && (
        <div className="bg-[#0a0c12]/50 p-8 rounded-[40px] border border-white/5">
          <IterationChart history={steps} />
        </div>
      )}

      {/* Iteration Cards */}
      {steps.length > 0 && (
        <div className="space-y-12">
          <h2 className="text-sm font-black text-gray-500 uppercase tracking-[0.3em] pl-4 border-l-4 border-indigo-500">Iteration Intelligence</h2>
          {[...steps].reverse().map((step, idx) => {
            const prevPrompt = idx < steps.length - 1 ? steps[steps.length - 2 - idx].prompt : null;
            const scoreDelta = idx < steps.length - 1
              ? step.averageScore - steps[steps.length - 2 - idx].averageScore
              : 0;

            return (
              <IterationCard
                key={step.iteration}
                step={step}
                prevPrompt={prevPrompt}
                scoreDelta={scoreDelta}
                showRowDetails={true}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ExperimentDetailView;
