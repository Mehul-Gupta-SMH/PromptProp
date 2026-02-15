
import React, { useState, useMemo } from 'react';
import { 
  DatasetRow, IterationStep, LLMProvider, 
  AppState, TestCaseResult, ProviderKeys, JuryMember, ModelSettings 
} from './types';
import * as gemini from './services/apiService';
import DatasetTable from './components/DatasetTable';
import IterationChart from './components/IterationChart';

const INITIAL_PROMPT = "You are a professional assistant. Help the user with their request.";

const GEMINI_MODELS = [
  { id: 'gemini-3-flash-preview', name: 'Gemini 3 Flash' },
  { id: 'gemini-3-pro-preview', name: 'Gemini 3 Pro' },
  { id: 'gemini-2.5-flash-lite-latest', name: 'Gemini Flash Lite' },
];

// Helper to calculate simple line-based diff
const getLineDiff = (oldText: string, newText: string) => {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  return {
    removed: oldLines.filter(line => !newLines.includes(line) && line.trim().length > 0),
    added: newLines.filter(line => !oldLines.includes(line) && line.trim().length > 0)
  };
};

const App: React.FC = () => {
  const [state, setState] = useState<AppState>({
    taskDescription: "Categorize customer feedback into: Product, Billing, Shipping, or General. For Billing, always mention the refund policy.",
    basePrompt: INITIAL_PROMPT,
    dataset: [],
    runnerModel: { 
      provider: LLMProvider.GEMINI, 
      model: 'gemini-3-flash-preview', 
      settings: { temperature: 0.1, topP: 0.95, topK: 40 } 
    },
    juryMembers: [
      { 
        id: 'j1', 
        name: 'Senior Analyst Jury', 
        provider: LLMProvider.GEMINI, 
        model: 'gemini-3-pro-preview', 
        settings: { temperature: 0 } 
      }
    ],
    keys: { gemini: '', openai: '', anthropic: '' },
    refinementHistory: [],
    isOptimizing: false,
    currentIteration: 0,
    optimizationStatus: { stage: 'idle', completedItems: 0, totalItems: 0, currentMessage: '' }
  });

  const [showAddJury, setShowAddJury] = useState(false);
  const [newJury, setNewJury] = useState<Partial<JuryMember>>({
    name: '',
    model: 'gemini-3-pro-preview',
    settings: { temperature: 0 }
  });

  const startOptimization = async () => {
    if (state.dataset.length === 0) return alert("Please add at least one test case to the dataset.");
    if (state.juryMembers.length === 0) return alert("Please add at least one jury member.");

    setState(prev => ({ 
      ...prev, 
      isOptimizing: true, 
      refinementHistory: [],
      optimizationStatus: { 
        stage: 'inference', 
        completedItems: 0, 
        totalItems: state.dataset.length, 
        currentMessage: 'Calibrating AI Jury Ensemble...' 
      }
    }));
    
    let currentPrompt = state.basePrompt;
    let iteration = 1;
    let prevScore = -1;
    const MAX_ITERATIONS = 5;

    try {
      while (iteration <= MAX_ITERATIONS) {
        setState(prev => ({ 
          ...prev, 
          currentIteration: iteration,
          optimizationStatus: { 
            stage: 'inference', 
            completedItems: 0, 
            totalItems: state.dataset.length, 
            currentMessage: `Cycle ${iteration}: Executing Inference...` 
          } 
        }));

        const testResults: TestCaseResult[] = [];
        
        for (let i = 0; i < state.dataset.length; i++) {
          const row = state.dataset[i];
          
          const actualOutput = await gemini.runInference(
            state.runnerModel.model,
            state.taskDescription,
            currentPrompt,
            row.query,
            state.runnerModel.settings
          );

          setState(prev => ({ 
            ...prev, 
            optimizationStatus: { 
              ...prev.optimizationStatus, 
              stage: 'jury', 
              currentMessage: `Cycle ${iteration}: Validating Case ${i+1}/${state.dataset.length}...` 
            } 
          }));

          const juryEvals = await Promise.all(
            state.juryMembers.map(jury => 
              gemini.evaluateWithJury(jury, state.taskDescription, row, actualOutput)
                .then(res => ({ juryName: jury.name, score: res.score, reasoning: res.reasoning }))
            )
          );

          const avg = juryEvals.reduce((s, e) => s + e.score, 0) / juryEvals.length;
          const feedback = juryEvals.map(e => `[${e.juryName}]: ${e.reasoning}`).join("\n");

          testResults.push({
            rowId: row.id,
            actualOutput,
            scores: juryEvals,
            averageScore: avg,
            combinedFeedback: feedback
          });

          setState(prev => ({ 
            ...prev, 
            optimizationStatus: { 
              ...prev.optimizationStatus, 
              completedItems: i + 1, 
              stage: 'inference' 
            } 
          }));
        }

        const iterationAvg = testResults.reduce((s, r) => s + r.averageScore, 0) / testResults.length;
        
        const step: IterationStep = {
          iteration,
          prompt: currentPrompt,
          averageScore: iterationAvg,
          results: testResults,
          refinementFeedback: iteration === 1 ? "Baseline established." : "Analyzing propagation impact..."
        };

        // If we have a previous step, we can calculate a diff if we store it
        const previousStep = state.refinementHistory[state.refinementHistory.length - 1];

        setState(prev => ({ ...prev, refinementHistory: [...prev.refinementHistory, step] }));

        if (iterationAvg >= 98 || (prevScore !== -1 && Math.abs(iterationAvg - prevScore) < 0.2)) {
          setState(prev => ({ 
            ...prev, 
            optimizationStatus: { ...prev.optimizationStatus, stage: 'complete', currentMessage: 'Optimization convergence achieved.' } 
          }));
          break;
        }

        setState(prev => ({ 
          ...prev, 
          optimizationStatus: { 
            stage: 'refinement', 
            completedItems: 0, 
            totalItems: 1, 
            currentMessage: `Cycle ${iteration}: Propagating back-prop updates...` 
          } 
        }));

        const failures = testResults
          .filter(r => r.averageScore < 90)
          .map(r => {
            const row = state.dataset.find(d => d.id === r.rowId);
            return `Query: ${row?.query}\nExpected: ${row?.expectedOutput}\nActual: ${r.actualOutput}\nCritique: ${r.combinedFeedback}`;
          })
          .join("\n---\n");

        const refinement = await gemini.refinePrompt(state.taskDescription, currentPrompt, failures);
        
        currentPrompt = refinement.refinedPrompt;
        step.refinementFeedback = `${refinement.explanation}\n\nImpact Analysis: ${refinement.deltaReasoning}`;

        prevScore = iterationAvg;
        iteration++;
        await new Promise(r => setTimeout(r, 1000));
      }
    } catch (err: any) {
      console.error(err);
      alert("Propagator encountered an error. Ensure API keys are correct and network is stable.");
    }

    setState(prev => ({ 
      ...prev, 
      isOptimizing: false,
      optimizationStatus: { ...prev.optimizationStatus, stage: 'idle', currentMessage: '' }
    }));
  };

  const addJuryMember = () => {
    if (!newJury.name) return alert("Enter a label for this judge.");
    const member: JuryMember = {
      id: Math.random().toString(36).substr(2, 9),
      name: newJury.name,
      provider: LLMProvider.GEMINI,
      model: newJury.model || 'gemini-3-pro-preview',
      settings: (newJury.settings || { temperature: 0 }) as ModelSettings
    };
    setState(prev => ({ ...prev, juryMembers: [...prev.juryMembers, member] }));
    setShowAddJury(false);
    setNewJury({ name: '', model: 'gemini-3-pro-preview', settings: { temperature: 0 } });
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-[#05070a] text-gray-100 font-sans selection:bg-indigo-500/30">
      
      {/* Sidebar - Control Hub */}
      <div className="w-full lg:w-[420px] bg-[#0a0c12] border-r border-white/5 p-6 overflow-y-auto flex-shrink-0 flex flex-col gap-6 shadow-2xl z-20">
        
        <header className="flex items-center gap-3 pb-2">
          <div className="w-10 h-10 bg-gradient-to-tr from-indigo-500 via-blue-600 to-cyan-500 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-white">PromptProp</h1>
            <p className="text-[10px] font-mono text-indigo-400/80 uppercase tracking-widest font-bold">Back-Prop Optimizer</p>
          </div>
        </header>

        <section className="space-y-2">
          <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Global Task Objective</label>
          <textarea 
            className="w-full bg-white/[0.03] border border-white/10 rounded-xl p-3 text-xs focus:border-indigo-500/40 outline-none min-h-[70px] resize-none transition-all placeholder:text-gray-700 leading-relaxed"
            placeholder="What is the ultimate goal of the prompt?"
            value={state.taskDescription}
            onChange={(e) => setState(p => ({ ...p, taskDescription: e.target.value }))}
          />
        </section>

        <section className="space-y-3">
          <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Primary Execution Model</label>
          <div className="space-y-2">
            <select 
              className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-indigo-500/40 appearance-none cursor-pointer"
              value={state.runnerModel.model}
              onChange={(e) => setState(p => ({ ...p, runnerModel: { ...p.runnerModel, model: e.target.value } }))}
            >
              {GEMINI_MODELS.map(m => <option key={m.id} value={m.id} className="bg-gray-950">{m.name}</option>)}
            </select>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-2 px-3">
                <span className="text-[9px] text-gray-600 uppercase font-bold block mb-1">Temp</span>
                <input 
                  type="number" step="0.1" min="0" max="2"
                  className="w-full bg-transparent text-xs outline-none text-indigo-300"
                  value={state.runnerModel.settings.temperature}
                  onChange={(e) => setState(p => ({ ...p, runnerModel: { ...p.runnerModel, settings: { ...p.runnerModel.settings, temperature: parseFloat(e.target.value) } } }))}
                />
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-2 px-3">
                <span className="text-[9px] text-gray-600 uppercase font-bold block mb-1">Top P</span>
                <input 
                  type="number" step="0.05" min="0" max="1"
                  className="w-full bg-transparent text-xs outline-none text-indigo-300"
                  value={state.runnerModel.settings.topP || 0.95}
                  onChange={(e) => setState(p => ({ ...p, runnerModel: { ...p.runnerModel, settings: { ...p.runnerModel.settings, topP: parseFloat(e.target.value) } } }))}
                />
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-2">
          <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Initial Prompt (Seed)</label>
          <textarea 
            className="w-full bg-white/[0.03] border border-white/10 rounded-xl p-3 text-xs font-mono focus:border-indigo-500/40 outline-none min-h-[120px] resize-none text-gray-300 leading-relaxed"
            value={state.basePrompt}
            onChange={(e) => setState(p => ({ ...p, basePrompt: e.target.value }))}
          />
        </section>

        <section className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Jury Panel</label>
            <button 
              onClick={() => setShowAddJury(!showAddJury)}
              className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-tight"
            >
              {showAddJury ? 'Dismiss' : '+ New Judge'}
            </button>
          </div>

          {showAddJury && (
            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-4 space-y-3 animate-in fade-in slide-in-from-top-2">
              <input 
                placeholder="Judge Alias..."
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-indigo-500/40"
                value={newJury.name}
                onChange={(e) => setNewJury(p => ({ ...p, name: e.target.value }))}
              />
              <select 
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs outline-none"
                value={newJury.model}
                onChange={(e) => setNewJury(p => ({ ...p, model: e.target.value }))}
              >
                {GEMINI_MODELS.map(m => <option key={m.id} value={m.id} className="bg-gray-900">{m.name}</option>)}
              </select>
              <button 
                onClick={addJuryMember}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-black transition-all shadow-lg shadow-indigo-900/40"
              >
                Assemble
              </button>
            </div>
          )}

          <div className="space-y-2">
            {state.juryMembers.map(m => (
              <div key={m.id} className="group relative bg-white/[0.02] border border-white/5 rounded-2xl p-3 px-4 flex justify-between items-center hover:bg-white/[0.04] transition-all">
                <div>
                  <h4 className="text-xs font-bold text-gray-200">{m.name}</h4>
                  <p className="text-[9px] text-gray-600 font-mono uppercase tracking-tighter">{m.model} / {m.settings.temperature}T</p>
                </div>
                <button 
                  onClick={() => setState(prev => ({ ...prev, juryMembers: prev.juryMembers.filter(jm => jm.id !== m.id) }))}
                  className="opacity-0 group-hover:opacity-100 p-2 text-gray-600 hover:text-red-500 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </section>

        <button
          onClick={startOptimization}
          disabled={state.isOptimizing}
          className={`mt-auto w-full py-4 rounded-2xl font-black text-sm uppercase tracking-[0.2em] transition-all shadow-2xl flex items-center justify-center gap-3
            ${state.isOptimizing 
              ? 'bg-gray-900 text-gray-700 cursor-not-allowed border border-white/5' 
              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-950/40 active:scale-[0.97]'}`}
        >
          {state.isOptimizing ? 'Back-Propagating...' : 'Propagate Lift'}
        </button>
      </div>

      {/* Main Workspace */}
      <main className="flex-1 overflow-y-auto p-6 lg:p-12 relative bg-[#05070a]">
        <div className="max-w-5xl mx-auto space-y-12 pb-32">
          
          <DatasetTable data={state.dataset} setData={(d) => setState(p => ({ ...p, dataset: d }))} />

          {state.isOptimizing && (
            <div className="bg-indigo-600/[0.03] border border-indigo-500/20 rounded-[32px] p-10 backdrop-blur-3xl animate-in fade-in zoom-in duration-500">
              <div className="flex justify-between items-end mb-8">
                <div>
                  <h3 className="text-xs font-black text-indigo-400 uppercase tracking-widest mb-2 flex items-center gap-3">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse shadow-[0_0_10px_rgba(99,102,241,1)]"></span>
                    Propagation Phase: {state.optimizationStatus.stage}
                  </h3>
                  <p className="text-2xl font-bold text-indigo-500 drop-shadow-sm">{state.optimizationStatus.currentMessage}</p>
                </div>
                <div className="text-right">
                  <span className="block text-5xl font-black text-indigo-500/40 font-mono tabular-nums leading-none">
                    {Math.round((state.optimizationStatus.completedItems / (state.optimizationStatus.totalItems || 1)) * 100)}%
                  </span>
                </div>
              </div>
              <div className="h-3 w-full bg-gray-900 rounded-full overflow-hidden border border-white/5 shadow-inner">
                <div 
                  className="h-full bg-gradient-to-r from-indigo-600 via-blue-500 to-cyan-400 transition-all duration-1000 ease-out shadow-[0_0_20px_rgba(99,102,241,0.3)]" 
                  style={{ width: `${(state.optimizationStatus.completedItems / (state.optimizationStatus.totalItems || 1)) * 100}%` }}
                ></div>
              </div>
            </div>
          )}

          {state.refinementHistory.length > 0 && (
            <div className="space-y-16 animate-in fade-in slide-in-from-bottom-8 duration-1000">
              
              <div className="bg-[#0a0c12]/50 p-8 rounded-[40px] border border-white/5">
                 <IterationChart history={state.refinementHistory} />
              </div>
              
              <div className="space-y-12">
                <h2 className="text-sm font-black text-gray-500 uppercase tracking-[0.3em] pl-4 border-l-4 border-indigo-500">Iteration Intelligence</h2>
                {[...state.refinementHistory].reverse().map((step, idx) => {
                  const prevPrompt = idx < state.refinementHistory.length - 1 ? state.refinementHistory[state.refinementHistory.length - 2 - idx].prompt : null;
                  const diff = prevPrompt ? getLineDiff(prevPrompt, step.prompt) : null;
                  const scoreDelta = idx < state.refinementHistory.length - 1 
                    ? step.averageScore - state.refinementHistory[state.refinementHistory.length - 2 - idx].averageScore
                    : 0;

                  return (
                    <div key={idx} className="bg-[#0a0c12]/80 border border-white/5 rounded-[40px] overflow-hidden shadow-2xl backdrop-blur-xl group hover:border-indigo-500/20 transition-all duration-500">
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
                                  {scoreDelta > 0 ? '▲' : '▼'} {Math.abs(scoreDelta).toFixed(1)}
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

                        <div className="pt-4">
                          <details className="group">
                            <summary className="text-[10px] font-black text-gray-500 uppercase tracking-widest cursor-pointer hover:text-indigo-400 transition-colors list-none flex items-center gap-2">
                              <span className="group-open:rotate-90 transition-transform">▶</span>
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
                })}
              </div>
            </div>
          )}

          {state.refinementHistory.length === 0 && !state.isOptimizing && (
            <div className="h-[600px] flex flex-col items-center justify-center text-center space-y-10 opacity-40 select-none border-4 border-dashed border-white/[0.02] rounded-[60px]">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-500 blur-[100px] opacity-10"></div>
                <div className="relative w-32 h-32 bg-[#0a0c12] rounded-[3rem] flex items-center justify-center border border-white/10 shadow-3xl">
                  <svg className="w-16 h-16 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                </div>
              </div>
              <div className="space-y-4 px-10">
                <h2 className="text-3xl font-black tracking-tighter text-white/50">Core Optimizer Idle</h2>
                <p className="text-base max-w-md mx-auto text-gray-500 leading-relaxed font-medium">
                  Populate your test suite and assemble your jury. The propagation engine will handle the heavy lifting of prompt refinement.
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
