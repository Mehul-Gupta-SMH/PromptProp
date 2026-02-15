# API Reference

Base URL: `http://localhost:8000`

## Core Endpoints

### POST /api/inference
Run a prompt against a single test case.

**Request:**
```json
{
  "model": "gemini-3-flash-preview",
  "taskDescription": "Categorize customer feedback",
  "promptTemplate": "You are a classifier...",
  "query": "My package arrived damaged",
  "settings": { "temperature": 0.1, "topP": 0.95, "topK": 40 }
}
```

**Response:**
```json
{ "output": "Category: Shipping\nThe customer reports..." }
```

### POST /api/jury
Evaluate model output using a jury member.

**Request:**
```json
{
  "juryModel": "gemini-3-pro-preview",
  "jurySettings": { "temperature": 0 },
  "taskDescription": "Categorize customer feedback",
  "row": {
    "query": "My package arrived damaged",
    "expectedOutput": "Shipping",
    "softNegatives": "Don't be verbose",
    "hardNegatives": "Never say Billing for shipping issues"
  },
  "actualOutput": "Category: Shipping"
}
```

**Response:**
```json
{ "score": 92.0, "reasoning": "Correctly identified as Shipping..." }
```

### POST /api/refine
Refine a prompt based on failure feedback.

**Request:**
```json
{
  "taskDescription": "Categorize customer feedback",
  "currentPrompt": "You are a classifier...",
  "failures": "Query: ...\nExpected: ...\nActual: ...\nCritique: ..."
}
```

**Response:**
```json
{
  "explanation": "Added explicit category definitions",
  "refinedPrompt": "You are a classifier. Categories are...",
  "deltaReasoning": "Failures showed category confusion..."
}
```

## Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Welcome message |
| `/health-check` | GET | Returns `{"status": "healthy"}` |

## Error Responses
- `502 Bad Gateway` — LLM call failed (auth error, rate limit, bad request)
- `422 Unprocessable Entity` — Invalid request body (Pydantic validation)
