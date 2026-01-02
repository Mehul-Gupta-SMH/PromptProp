
export enum LLMProvider {
  GEMINI = 'gemini',
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
  optimizationStatus: OptimizationStatus;
}
