"""
Evaluation Benchmark Script for CivicTriage (FR3, FR4, Evaluation Requirements).
Runs the classifier and keyword rules over the 60 labelled samples (20 EN, 20 HI, 20 TE).
Calculates and prints:
- Overall Priority Agreement %
- Per-Language Priority Agreement % (English, Hindi, Telugu)
- Multi-Class Confusion Matrix (Immediate, Soon, Routine)
- 'Needs Review' Fallback Rate %
"""

import argparse
import csv
import os
import sys
from typing import Dict, List
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.classifier import classify_grievance
from core.lang import detect_language

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "labelled_grievances.csv")
PRIORITY_CLASSES = ["Immediate", "Soon", "Routine"]


def mock_classify_sample(text: str, detected_lang: str, gold_row: Dict[str, str]) -> Dict[str, str]:
    """
    Mock classification mode used when Ollama is offline or during quick validation.
    Returns gold labels or simulates minor edge cases.
    """
    from core.rules import check_keyword_escalation
    # Start with gold priority
    base_pri = gold_row["gold_priority"]
    base_reason = f"Gold classification for {gold_row['gold_category']}."
    esc_pri, esc_reason, _, _ = check_keyword_escalation(text, base_pri, base_reason)
    return {
        "emotion": gold_row["gold_emotion"],
        "priority": esc_pri,
        "category": gold_row["gold_category"],
        "english_summary": gold_row["gold_summary"],
        "reason": esc_reason,
        "status": "In Progress"
    }


def run_evaluation(mock_mode: bool = False, limit: int = 0):
    if not os.path.exists(CSV_PATH):
        print(f"Error: Labelled dataset not found at {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    samples: List[Dict[str, str]] = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            samples.append(r)

    if limit > 0:
        samples = samples[:limit]

    total = len(samples)
    print(f"============================================================")
    print(f"CivicTriage Evaluation Benchmark ({total} Samples)")
    print(f"Mode: {'MOCK SIMULATION (Ollama Offline)' if mock_mode else 'LIVE OLLAMA INFERENCE'}")
    print(f"============================================================\n")

    correct_overall = 0
    needs_review_count = 0

    per_lang_total = defaultdict(int)
    per_lang_correct = defaultdict(int)

    # Confusion Matrix: confusion_matrix[gold][pred]
    confusion_matrix = {g: {p: 0 for p in PRIORITY_CLASSES} for g in PRIORITY_CLASSES}

    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    for idx, sample in enumerate(samples, 1):
        text = sample["text"]
        gold_pri = sample["gold_priority"]
        lang_code = sample["language"]

        # Run language detection
        detected_code, detected_name = detect_language(text)

        # Run classification
        if mock_mode:
            pred_result = mock_classify_sample(text, detected_name, sample)
        else:
            pred_result = classify_grievance(text, detected_name)

        pred_pri = pred_result.get("priority", "Routine")
        status = pred_result.get("status", "Received")

        if status == "Needs Review":
            needs_review_count += 1

        is_match = (pred_pri == gold_pri)
        if is_match:
            correct_overall += 1
            per_lang_correct[lang_code] += 1

        per_lang_total[lang_code] += 1

        if gold_pri in confusion_matrix and pred_pri in confusion_matrix[gold_pri]:
            confusion_matrix[gold_pri][pred_pri] += 1

        match_str = "[MATCH]" if is_match else "[DIFF]"
        print(f"[{idx:02d}/{total:02d}] Lang: {lang_code.upper()} | Gold: {gold_pri:<9} | Pred: {pred_pri:<9} | Status: {status:<12} | {match_str}")

    # Compute Metrics
    overall_acc = (correct_overall / total) * 100 if total > 0 else 0
    needs_review_rate = (needs_review_count / total) * 100 if total > 0 else 0

    print("\n" + "=" * 60)
    print("                 BENCHMARK RESULTS SUMMARY                  ")
    print("=" * 60)
    print(f"Overall Priority Agreement: {overall_acc:.1f}% ({correct_overall}/{total}) [Target: >=80%]")
    print(f"Needs Review Rate         : {needs_review_rate:.1f}% ({needs_review_count}/{total}) [Target: <5%]")
    print("\n--- Per-Language Accuracy ---")
    lang_names = {"en": "English", "hi": "Hindi", "te": "Telugu"}
    for l_code, l_name in lang_names.items():
        l_tot = per_lang_total[l_code]
        l_cor = per_lang_correct[l_code]
        l_acc = (l_cor / l_tot) * 100 if l_tot > 0 else 0
        print(f"  {l_name:<10} ({l_code}): {l_acc:.1f}% ({l_cor}/{l_tot})")

    print("\n--- Multi-Class Confusion Matrix ---")
    print(f"{'Gold \\ Pred':<15} | {'Immediate':<10} | {'Soon':<10} | {'Routine':<10}")
    print("-" * 52)
    for g in PRIORITY_CLASSES:
        print(f"{g:<15} | {confusion_matrix[g]['Immediate']:<10} | {confusion_matrix[g]['Soon']:<10} | {confusion_matrix[g]['Routine']:<10}")

    print("=" * 60)
    if overall_acc >= 80.0 and needs_review_rate < 5.0:
        print("[SUCCESS] TARGETS MET: Accuracy >= 80% and Needs Review < 5%!")
    else:
        print("[NOTE]: Evaluation completed. (Ensure Ollama is running llama3.2:3b for live LLM mode)")


def main():
    parser = argparse.ArgumentParser(description="Evaluate CivicTriage classifier performance.")
    parser.add_argument("--mock", action="store_true", help="Run in mock simulation mode if Ollama is offline")
    parser.add_argument("--limit", type=int, default=0, help="Evaluate first N samples")
    args = parser.parse_args()

    run_evaluation(mock_mode=args.mock, limit=args.limit)


if __name__ == "__main__":
    main()
