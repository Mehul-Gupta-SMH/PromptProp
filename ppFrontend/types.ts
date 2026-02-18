
export enum LLMProvider {
  GEMINI = 'gemini',
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
}

export interface ModelSettings {
  temperature: number;
  topK?: number;
  topP?: number;
}

export interface JuryMember {
  id: string;
  name: string;
  provider: LLMProvider;
  model: string;
  settings: ModelSettings;
}

export interface ProviderKeys {
  gemini: string;
  openai: string;
  anthropic: string;
}

export interface DatasetRow {
  id: string;
  query: string;
  expectedOutput: string;
  softNegatives?: string;
  hardNegatives?: string;
}

export interface TestCaseResult {
  rowId: string;
  actualOutput: string;
  scores: Array<{ juryName: string; score: number; reasoning: string }>;
  averageScore: number;
  combinedFeedback: string;
}

export interface IterationStep {
  iteration: number;
  prompt: string;
  averageScore: number;
  results: TestCaseResult[];
  refinementFeedback: string;
}

export interface OptimizationStatus {
  stage: 'idle' | 'inference' | 'jury' | 'refinement' | 'complete';
  completedItems: number;
  totalItems: number;
  currentMessage: string;
}

export interface TokenUsageBreakdown {
  inference: number;
  jury: number;
  refinement: number;
  total: number;
}

export interface OptimizeSSEEvent {
  event: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

// ---------------------------------------------------------------------------
// Experiment History types
// ---------------------------------------------------------------------------

export interface ExperimentSummary {
  id: string;
  name: string | null;
  taskDescription: string;
  basePrompt: string;
  runnerModel: Record<string, unknown>;
  isComplete: boolean;
  createdAt: string;
  updatedAt: string;
  iterationCount: number;
  bestScore: number | null;
  finalScore: number | null;
  datasetSize: number;
}

export interface ExperimentListResponse {
  experiments: ExperimentSummary[];
  total: number;
}

export interface JuryEvaluationDetail {
  id: string;
  juryMemberId: string;
  juryName: string;
  score: number;
  reasoning: string;
}

export interface IterationResultDetail {
  id: string;
  datasetRowId: string;
  actualOutput: string;
  averageScore: number | null;
  combinedFeedback: string | null;
  juryEvaluations: JuryEvaluationDetail[];
}

export interface PromptVersionDetail {
  id: string;
  iterationNumber: number;
  promptText: string;
  averageScore: number | null;
  refinementFeedback: string | null;
  refinementMeta: Record<string, unknown> | null;
  results: IterationResultDetail[];
}

export interface JuryMemberDetail {
  id: string;
  name: string;
  provider: string;
  model: string;
  settings: Record<string, unknown>;
}

export interface DatasetRowDetail {
  id: string;
  split: string;
  query: string;
  expectedOutput: string;
  softNegatives: string | null;
  hardNegatives: string | null;
}

export interface ExperimentDetail {
  id: string;
  name: string | null;
  taskDescription: string;
  basePrompt: string;
  runnerModel: Record<string, unknown>;
  isComplete: boolean;
  createdAt: string;
  updatedAt: string;
  juryMembers: JuryMemberDetail[];
  datasetRows: DatasetRowDetail[];
  promptVersions: PromptVersionDetail[];
}

export interface AppState {
  taskDescription: string;
  basePrompt: string;
  dataset: DatasetRow[];
  runnerModel: { 
    provider: LLMProvider; 
    model: string; 
    settings: ModelSettings 
  };
  juryMembers: JuryMember[];
  keys: ProviderKeys;
  refinementHistory: IterationStep[];
  isOptimizing: boolean;
  currentIteration: number;
  managerModel: {
    model: string;
    settings: ModelSettings;
  };
  optimizationStatus: OptimizationStatus;
  tokenUsage: TokenUsageBreakdown;
}
