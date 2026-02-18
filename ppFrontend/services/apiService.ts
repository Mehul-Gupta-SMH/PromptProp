import { DatasetRow, ModelSettings, JuryMember, OptimizeSSEEvent, ExperimentListResponse, ExperimentDetail } from '../types';

const API_BASE = '/api';

async function get<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

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


// ---------------------------------------------------------------------------
// Experiment history
// ---------------------------------------------------------------------------

export const listExperiments = async (
  limit = 50,
  offset = 0
): Promise<ExperimentListResponse> => {
  return get<ExperimentListResponse>(`/experiments?limit=${limit}&offset=${offset}`);
};

export const getExperimentDetail = async (
  id: string
): Promise<ExperimentDetail> => {
  return get<ExperimentDetail>(`/experiments/${id}`);
};


// ---------------------------------------------------------------------------
// SSE streaming optimization
// ---------------------------------------------------------------------------

export interface OptimizeRequestPayload {
  taskDescription?: string;
  basePrompt?: string;
  dataset?: Array<{
    query: string;
    expectedOutput: string;
    softNegatives?: string | null;
    hardNegatives?: string | null;
  }>;
  juryMembers?: Array<{
    name: string;
    provider?: string;
    model: string;
    settings?: ModelSettings;
  }>;
  runnerModel?: {
    provider?: string;
    model: string;
    settings?: ModelSettings;
  };
  managerModel?: {
    model: string;
    settings?: ModelSettings;
  };
  experimentId?: string;
  maxIterations?: number;
  convergenceThreshold?: number;
  passThreshold?: number;
  perfectScore?: number;
}

/**
 * Start an optimization loop via POST /api/optimize and consume SSE events.
 *
 * Uses fetch() + ReadableStream because EventSource only supports GET.
 * Calls `onEvent` for each parsed SSE event. Returns when the stream ends.
 */
export const startOptimizeStream = async (
  payload: OptimizeRequestPayload,
  onEvent: (event: OptimizeSSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> => {
  const response = await fetch(`${API_BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse complete SSE frames from buffer
    const frames = buffer.split('\n\n');
    // Last element may be incomplete — keep it in buffer
    buffer = frames.pop() || '';

    for (const frame of frames) {
      if (!frame.trim()) continue;

      let eventType = 'message';
      let dataStr = '';

      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          dataStr += line.slice(6);
        }
      }

      if (dataStr) {
        try {
          const data = JSON.parse(dataStr);
          onEvent({ event: eventType, data });
        } catch {
          console.warn('Failed to parse SSE data:', dataStr);
        }
      }
    }
  }
};
