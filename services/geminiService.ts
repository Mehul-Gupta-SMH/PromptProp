
import { GoogleGenAI, Type } from "@google/genai";
import { DatasetRow, TestCaseResult, ModelSettings, LLMProvider, JuryMember } from "../types";

/**
 * Standard schemas for structured outputs
 */
export const JURY_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    score: { type: Type.NUMBER, description: "Score from 0 to 100" },
    reasoning: { type: Type.STRING, description: "Detailed critique" }
  },
  required: ["score", "reasoning"]
};

export const REFINEMENT_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    explanation: { type: Type.STRING, description: "Brief summary of what was changed" },
    refinedPrompt: { type: Type.STRING, description: "The complete new version of the prompt" },
    deltaReasoning: { type: Type.STRING, description: "Why this specific change is expected to improve performance based on previous failures" }
  },
  required: ["explanation", "refinedPrompt", "deltaReasoning"]
};

/**
 * Run inference for a single test case
 */
export const runInference = async (
  model: string,
  taskDescription: string,
  promptTemplate: string,
  query: string,
  settings: ModelSettings
): Promise<string> => {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  const fullPrompt = `Task Context: ${taskDescription}\n\nInstruction: ${promptTemplate}\n\nInput: ${query}`;
  
  const response = await ai.models.generateContent({
    model: model,
    contents: fullPrompt,
    config: {
      temperature: settings.temperature,
      topK: settings.topK,
      topP: settings.topP,
    },
  });

  return response.text || "No response generated.";
};

/**
 * Perform Jury evaluation with specific model and settings
 */
export const evaluateWithJury = async (
  jury: JuryMember,
  taskDescription: string,
  row: DatasetRow,
  actualOutput: string
): Promise<{ score: number; reasoning: string }> => {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  
  const juryPrompt = `
    TASK CONTEXT: ${taskDescription}
    USER QUERY: ${row.query}
    EXPECTED OUTPUT: ${row.expectedOutput}
    SOFT NEGATIVES: ${row.softNegatives || 'None'}
    HARD NEGATIVES: ${row.hardNegatives || 'None'}
    
    AI OUTPUT TO EVALUATE: 
    """
    ${actualOutput}
    """
    
    Evaluate the AI output objectively based on the criteria. Return a score from 0 to 100.
    Be strict. If it hits a hard negative, score below 40.
  `;

  const response = await ai.models.generateContent({
    model: jury.model,
    contents: juryPrompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: JURY_SCHEMA,
      temperature: jury.settings.temperature,
      topK: jury.settings.topK,
      topP: jury.settings.topP,
    }
  });

  try {
    return JSON.parse(response.text || "{}");
  } catch {
    return { score: 0, reasoning: "Error parsing jury response." };
  }
};

/**
 * Back-propagate feedback to refine the prompt
 */
export const refinePrompt = async (
  taskDescription: string,
  currentPrompt: string,
  failures: string
): Promise<{ explanation: string; refinedPrompt: string; deltaReasoning: string }> => {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  
  const refinerPrompt = `
    You are a Prompt Meta-Optimizer. 
    TASK: ${taskDescription}
    
    CURRENT PROMPT:
    """
    ${currentPrompt}
    """
    
    CRITIQUE FROM FAILED TEST CASES (BACK-PROPAGATED ERROR):
    ${failures}
    
    INSTRUCTIONS:
    1. Identify exactly where the current prompt fails to guide the model.
    2. Rewrite the prompt to fix these specific issues.
    3. Keep existing successes intact.
    4. Provide a "deltaReasoning" explaining why this change specifically targets the observed failures.
  `;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: refinerPrompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: REFINEMENT_SCHEMA,
      temperature: 0.2
    }
  });

  try {
    return JSON.parse(response.text || "{}");
  } catch {
    return { explanation: "Failed to refine.", refinedPrompt: currentPrompt, deltaReasoning: "None" };
  }
};
