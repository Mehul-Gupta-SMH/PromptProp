
# PromptProp: AI-Driven Prompt Refinement

PromptProp is a high-fidelity prompt engineering platform that applies "back-propagation" concepts to natural language instructions. It iteratively optimizes a prompt against a "Ground Truth" dataset using an ensemble of AI judges to maximize quality and alignment.

## 🚀 Key Features

- **Primary Inference Control**: Select from various Gemini models (3 Pro, 3 Flash, Lite) for the task execution.
- **Ensemble Jury Panel**: Add multiple judges with unique configurations (Temperature, Top P/K) to critique the AI's output.
- **Meta-Refinement**: Uses a high-reasoning model (Gemini 3 Pro) to act as an "optimizer" that updates instructions based on failure feedback.
- **Progress Tracking**: Real-time visualization of performance lift across iterations.

---

## 🛠 Feature Roadmap

### 🔴 MUST ADD (Stability & Core)
- **Local Persistence**: Save datasets and optimization histories to Browser's IndexedDB.
- **Comparative Diff**: A text diff view showing exactly what lines changed in the prompt between Iteration X and Y.
- **Few-Shot Engine**: Automatically extract successful test cases and inject them as `Few-Shot` examples in the optimized prompt.
- **Token Usage Monitor**: Real-time tracking of token consumption per iteration.

### 🟡 SHOULD ADD (Usability & Depth)
- **Export to Production**: One-click download of the "Golden Prompt" in JSON, Python, or Markdown formats.
- **Synthetic Data Generation**: Use AI to generate "Edge Case" test data based on the task description.
- **Human-in-the-Loop**: A button to "Pause & Override" where a human can manually correct the Jury's score.
- **Model Versioning**: Support for specific model snapshots (e.g. `gemini-1.5-pro-002`).

### 🟢 COULD ADD (Advanced Innovation)
- **Variable Injection**: Dynamic placeholders (e.g., `{{user_name}}`) with schema validation.
- **Multi-Modal Back-Prop**: Support for optimizing prompts involving image or audio inputs.
- **Benchmarking Mode**: Run multiple "Starting Prompts" in parallel to find the best seed.
- **Prompt Linting**: Static analysis of prompts to find common pitfalls (e.g., conflicting constraints).

---

## ⚙️ Quick Start

1. **Environment**: Ensure your environment has a valid Gemini API Key injected.
2. **Define Task**: Enter your goal (e.g., "Helpdesk agent categorization").
3. **Dataset**: Load your examples into the Ground Truth table.
4. **Ensemble**: Add a few judges (one with low temp for consistency, one with high for diversity).
5. **Optimize**: Click **"Initiate Cycle"** and watch the performance lift.
