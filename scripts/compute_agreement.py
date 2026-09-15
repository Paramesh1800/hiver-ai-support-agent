import sys
import os
import io
import json
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RESULTS_DIR
from src.judge import LLMReplyJudge

HUMAN_SCORES_FILE = RESULTS_DIR / 'human_scores.json'
AGREEMENT_OUTPUT_FILE = RESULTS_DIR / 'judge_human_agreement.json'

def compute_agreement():
    if not HUMAN_SCORES_FILE.exists():
        print(f'Error: Human scores file not found at {HUMAN_SCORES_FILE}.')
        print('Please run human scoring CLI first: python -m scripts.score_replies')
        sys.exit(1)

    with open(HUMAN_SCORES_FILE, 'r', encoding='utf-8') as f:
        human_data = json.load(f)

    if not human_data:
        print('Error: human_scores.json is empty. Please run: python -m scripts.score_replies')
        sys.exit(1)

    if isinstance(human_data, dict):
        items = list(human_data.values())
    else:
        items = human_data

    sample_size = len(items)
    print('\n=======================================================')
    print('     COMPUTING HUMAN VS. LLM JUDGE AGREEMENT           ')
    print('=======================================================')
    print(f'Loaded {sample_size} human-scored items from {HUMAN_SCORES_FILE}')
    print('Evaluating blinded LLM Judge on the exact same candidate replies...\n')

    judge = LLMReplyJudge()

    human_overall = []
    judge_overall = []

    human_axes = {'groundedness': [], 'correctness': [], 'tone_fit': [], 'actionability': []}
    judge_axes = {'groundedness': [], 'correctness': [], 'tone_fit': [], 'actionability': []}

    print('ITEM ID      | HUMAN  | JUDGE  | DELTA  | G (H/J)   | C (H/J)   | T (H/J)   | A (H/J)')
    print('-' * 85)

    comparison_details = []

    for item in items:
        item_id = item['id']
        raw_text = item['raw_text']
        ref_reply = item['brand_reply_actual']
        draft_reply = item['candidate_draft_reply']

        h_g = int(item['groundedness'])
        h_c = int(item['correctness'])
        h_t = int(item['tone_fit'])
        h_a = int(item['actionability'])
        h_overall = float(item['overall_score'])

        j_eval = judge.evaluate_reply_blinded(raw_text, ref_reply, draft_reply)

        j_g = float(j_eval['groundedness'])
        j_c = float(j_eval['correctness'])
        j_t = float(j_eval['tone_fit'])
        j_a = float(j_eval['actionability'])
        j_overall = float(j_eval['overall_score'])

        human_overall.append(h_overall)
        judge_overall.append(j_overall)

        human_axes['groundedness'].append(h_g)
        judge_axes['groundedness'].append(j_g)
        human_axes['correctness'].append(h_c)
        judge_axes['correctness'].append(j_c)
        human_axes['tone_fit'].append(h_t)
        judge_axes['tone_fit'].append(j_t)
        human_axes['actionability'].append(h_a)
        judge_axes['actionability'].append(j_a)

        delta = round(abs(h_overall - j_overall), 2)

        print(f'{item_id:<12} | {h_overall:<6.2f} | {j_overall:<6.2f} | {delta:<6.2f} | {h_g}/{int(round(j_g)):<7} | {h_c}/{int(round(j_c)):<7} | {h_t}/{int(round(j_t)):<7} | {h_a}/{int(round(j_a)):<7}')

        comparison_details.append({
            'id': item_id,
            'human_overall': h_overall,
            'judge_overall': j_overall,
            'delta': delta,
            'human_scores': {'groundedness': h_g, 'correctness': h_c, 'tone_fit': h_t, 'actionability': h_a},
            'judge_scores': {'groundedness': j_g, 'correctness': j_c, 'tone_fit': j_t, 'actionability': j_a}
        })

    h_overall_int = [int(np.clip(round(x), 1, 5)) for x in human_overall]
    j_overall_int = [int(np.clip(round(x), 1, 5)) for x in judge_overall]

    kappa_overall = float(cohen_kappa_score(h_overall_int, j_overall_int, weights='quadratic', labels=[1, 2, 3, 4, 5]))
    
    if len(set(human_overall)) > 1 and len(set(judge_overall)) > 1:
        spearman_res = spearmanr(human_overall, judge_overall)
        spearman_corr = float(spearman_res.statistic)
    else:
        spearman_corr = 0.0

    print('-' * 85)
    print('\n=======================================================')
    print('              SUMMARY AGREEMENT METRICS                ')
    print('=======================================================')
    print(f'  Sample Size (n):                         {sample_size} items')
    print(f'  Quadratic Weighted Cohen\'s Kappa (k):    k = {kappa_overall:.4f}')
    print(f'  Spearman Correlation (r):                r = {spearman_corr:.4f}')

    axis_metrics = {}
    for axis in ['groundedness', 'correctness', 'tone_fit', 'actionability']:
        h_list = [int(x) for x in human_axes[axis]]
        j_list = [int(round(x)) for x in judge_axes[axis]]
        k_axis = float(cohen_kappa_score(h_list, j_list, weights='quadratic', labels=[1, 2, 3, 4, 5]))
        r_axis = float(spearmanr(h_list, j_list).statistic) if len(set(h_list)) > 1 and len(set(j_list)) > 1 else 0.0
        axis_metrics[axis] = {
            'cohens_kappa_quadratic': round(k_axis, 4),
            'spearman_correlation': round(r_axis, 4)
        }
        print(f'  - Axis {axis:<15}: Kappa = {k_axis:.4f} | Spearman = {r_axis:.4f}')

    if kappa_overall > 0.95:
        print('\n' + '='*85)
        print('⚠️ [CRITICAL SANITY WARNING]: Cohen\'s Kappa is suspiciously high (k > 0.95)!')
        print('   Real human-LLM agreement on subjective 1-5 rubrics rarely exceeds k = 0.70 - 0.85.')
        print('   Verify that human scores were entered manually in the terminal and NOT programmatically generated!')
        print('='*85 + '\n')

    if kappa_overall < 0.60:
        print('\n⚠️ [WARNING REPORT FINDING]: Cohen\'s Kappa is below 0.60 threshold (k < 0.60).')
        print('   This indicates moderate/low judge agreement and MUST be documented as a key limitation in REPORT.md.\n')
    else:
        print('\n✅ [PASSED]: Human-Judge agreement threshold met (k >= 0.60).\n')

    summary_results = {
        'sample_size': sample_size,
        'cohens_kappa_quadratic_overall': round(kappa_overall, 4),
        'spearman_correlation_overall': round(spearman_corr, 4),
        'judge_trustworthy': bool(kappa_overall >= 0.60),
        'per_axis_metrics': axis_metrics,
        'comparison_details': comparison_details
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(AGREEMENT_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary_results, f, indent=2, ensure_ascii=False)

    print(f'Agreement analysis saved to: {AGREEMENT_OUTPUT_FILE}\n')
    return summary_results

if __name__ == '__main__':
    compute_agreement()
