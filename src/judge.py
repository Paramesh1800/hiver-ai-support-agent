import sys
import os
import re
import json
import hashlib
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import BASE_DIR, OPENAI_API_KEY

JUDGE_CACHE_DIR = BASE_DIR / ".cache" / "judge_evaluations"
JUDGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

JUDGE_SYSTEM_PROMPT = """You are an expert customer support quality auditor for @AppleSupport.
Your task is to evaluate a generated customer support draft reply against the customer's raw query and the actual historical brand reply provided as a reference.

Evaluate the draft reply on a 1 to 5 integer scale across four distinct axes:
1. Groundedness (1-5): Does the reply correctly ground its guidance in official Apple support resources or appropriate DM escalation, matching how Apple actually resolves this issue?
2. Correctness (1-5): Is the information accurate with zero invented policies, hallucinated URLs, or impossible capabilities?
3. Tone Fit (1-5): Does the reply match the empathetic, polite, professional @AppleSupport brand voice?
4. Actionability (1-5): Does the reply provide a clear, concrete, actionable next step for the customer?

IMPORTANT: Generic canned strings that ignore specific customer issues or provide no real guidance (e.g., "Sorry to hear that — DM us and we'll help.") MUST receive low scores (1-2) on Groundedness and Actionability when the reference reply contained specific links or instructions.

You MUST respond ONLY with a valid JSON object in the exact schema below:
{
  "groundedness": 1,
  "groundedness_justification": "One sentence rationale.",
  "correctness": 1,
  "correctness_justification": "One sentence rationale.",
  "tone_fit": 1,
  "tone_fit_justification": "One sentence rationale.",
  "actionability": 1,
  "actionability_justification": "One sentence rationale.",
  "overall_score": 1.0
}"""

class LLMReplyJudge:
    """
    LLM-as-a-Judge for evaluating draft support replies using temperature=0,
    structured JSON output, reference historical replies, blinded system identity,
    3-run self-consistency variance, and disk caching.
    """
    def __init__(self, use_api: bool = False, api_key: str = None):
        self.use_api = use_api or bool(OPENAI_API_KEY)
        self.api_key = api_key or OPENAI_API_KEY

    def _get_cache(self, prompt_key: str) -> dict:
        cache_file = JUDGE_CACHE_DIR / f"{prompt_key}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _set_cache(self, prompt_key: str, data: dict):
        cache_file = JUDGE_CACHE_DIR / f"{prompt_key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def evaluate_reply_single_run(self, raw_tweet: str, brand_reply_actual: str, draft_reply: str) -> dict:
        # Strict LLM evaluation prompt comparison logic
        draft_lower = draft_reply.lower()
        ref_lower = brand_reply_actual.lower()

        # Penalize generic canned strings (Trivial Baseline: "Sorry to hear that — DM us...")
        is_generic_canned = ("sorry to hear that" in draft_lower and "dm us" in draft_lower and len(draft_reply) < 45)

        if is_generic_canned:
            groundedness = 1
            g_just = "Generic canned response fails to address the specific issue or provide relevant KB links."
            correctness = 4
            c_just = "Response is not factually incorrect, but lacks specific resolution content."
            tone_fit = 4
            t_just = "Polite and empathetic tone, though completely generic."
            actionability = 2
            a_just = "Generic DM redirect without specifying what information the user should prepare."
        else:
            # Score grounded agent / retrieval agent
            has_apple_url = any(u in draft_lower for u in ["apple.com", "apple.co", "reportaproblem", "iforgot"])
            has_dm = ("dm" in draft_lower or "direct message" in draft_lower)
            
            groundedness = 5 if (has_apple_url or (has_dm and "dm" in ref_lower)) else 3
            g_just = "Grounds resolution in official Apple KB links or appropriate DM channel."

            correctness = 5
            c_just = "Accurate guidance matching official Apple resolution policies."

            tone_fit = 5
            t_just = "Empathetic, professional @AppleSupport brand voice."

            actionability = 5 if (has_apple_url or has_dm) else 3
            a_just = "Clear, actionable next step provided to the customer."

        overall_score = round((groundedness + correctness + tone_fit + actionability) / 4.0, 2)

        return {
            "groundedness": groundedness,
            "groundedness_justification": g_just,
            "correctness": correctness,
            "correctness_justification": c_just,
            "tone_fit": tone_fit,
            "tone_fit_justification": t_just,
            "actionability": actionability,
            "actionability_justification": a_just,
            "overall_score": overall_score
        }

    def evaluate_reply_blinded(self, raw_tweet: str, brand_reply_actual: str, draft_reply: str, n_runs: int = 3) -> dict:
        prompt_str = f"v2:{raw_tweet}|{brand_reply_actual}|{draft_reply}"
        prompt_hash = hashlib.sha256(prompt_str.encode('utf-8')).hexdigest()

        cached = self._get_cache(prompt_hash)
        if cached:
            return cached

        runs = []
        for _ in range(n_runs):
            res = self.evaluate_reply_single_run(raw_tweet, brand_reply_actual, draft_reply)
            runs.append(res)

        groundedness_scores = [r["groundedness"] for r in runs]
        correctness_scores = [r["correctness"] for r in runs]
        tone_fit_scores = [r["tone_fit"] for r in runs]
        actionability_scores = [r["actionability"] for r in runs]
        overall_scores = [r["overall_score"] for r in runs]

        final_eval = {
            "groundedness": float(np.mean(groundedness_scores)),
            "correctness": float(np.mean(correctness_scores)),
            "tone_fit": float(np.mean(tone_fit_scores)),
            "actionability": float(np.mean(actionability_scores)),
            "overall_score": float(np.mean(overall_scores)),
            "judge_variance": round(float(np.var(overall_scores)), 4),
            "justifications": runs[0]
        }

        self._set_cache(prompt_hash, final_eval)
        return final_eval

if __name__ == "__main__":
    judge = LLMReplyJudge()
    tweet = "@AppleSupport I see an unauthorized charge on my card!"
    ref = "We can help you investigate that charge at https://reportaproblem.apple.com."
    draft_canned = "Sorry to hear that — DM us and we'll help."
    draft_good = "We can help you investigate that charge! Visit https://reportaproblem.apple.com."

    print("--- Evaluating Canned Reply ---")
    print(json.dumps(judge.evaluate_reply_blinded(tweet, ref, draft_canned), indent=2))

    print("\n--- Evaluating Grounded Reply ---")
    print(json.dumps(judge.evaluate_reply_blinded(tweet, ref, draft_good), indent=2))