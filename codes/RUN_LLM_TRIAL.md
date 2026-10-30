# Running the LLM harness (evaluation protocol, Section 5; not reported in this paper)

This takes about 10–30 minutes on a laptop with a GPU, and longer on CPU.

1. Install Ollama (https://ollama.com) and pull the model:
   `ollama pull qwen3:8b`
2. Make sure Ollama is running (`ollama serve`, or open the app).
3. From this folder (Python 3.10 or later, no extra packages):
   `python3 llm_trial.py --model qwen3:8b --reps 5`
   - Each of the five requests (L1–L5) is posed five times, with seeds 1–5 at temperature 0.7.
   - Each proposal goes through the admission gate. No approval is given.
4. Send back these three files:
   - `llm_trial_log.jsonl`: prompts, raw responses, parsed operations, outcomes and diagnostics.
   - `llm_trial_summary.md`
   - `llm_trial_table.tex`: a LaTeX table of the outcomes.

Options:
- `--host` if Ollama runs on another machine.
- `--temperature 0` for deterministic answers.
- `--model` for another local model.
- `python3 llm_trial.py --replay llm_trial_log.jsonl` re-runs the gate on recorded responses without calling the model.
- `python3 llm_trial.py --dry-run` tests the harness with canned responses. These are **not** model output.

If your own prototype has a different interface, it only needs to return one JSON proposal per request, in the format given in `SYSTEM` in `llm_trial.py`.
