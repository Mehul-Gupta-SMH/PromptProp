import { DatasetRow, ModelSettings, JuryMember } from '../types';

const API_BASE = '/api';

async function post<T>(endpoint: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const runInference = async (
  model: string,
  taskDescription: string,
  promptTemplate: string,
  query: string,
  settings: ModelSettings
): Promise<string> => {
  const result = await post<{ output: string }>('/inference', {
    model,
    taskDescription,
    promptTemplate,
    query,
    settings,
  });
  return result.output;
};

export const evaluateWithJury = async (
  jury: JuryMember,
  taskDescription: string,
  row: DatasetRow,
  actualOutput: string
): Promise<{ score: number; reasoning: string }> => {
  return post<{ score: number; reasoning: string }>('/jury', {
    juryModel: jury.model,
    jurySettings: jury.settings,
    taskDescription,
    row: {
      query: row.query,
      expectedOutput: row.expectedOutput,
      softNegatives: row.softNegatives || null,
      hardNegatives: row.hardNegatives || null,
    },
    actualOutput,
  });
};

export const refinePrompt = async (
  taskDescription: string,
  currentPrompt: string,
  failures: string
): Promise<{ explanation: string; refinedPrompt: string; deltaReasoning: string }> => {
  return post<{
    explanation: string;
    refinedPrompt: string;
    deltaReasoning: string;
  }>('/refine', {
    taskDescription,
    currentPrompt,
    failures,
  });
};
