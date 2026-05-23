"""
TrueSight evaluation harness.

Reads ground-truth labels from Test/README.md (the "Expected" column of the
markdown table), runs each labelled image through the detection pipeline,
and produces:

    1. A human-readable summary on stdout
    2. evaluation_results.json   — machine-readable per-image record
    3. evaluation_report.md      — dissertation-ready Markdown report

Rows whose Expected column says anything other than "Real" or starts-with
"AI" (i.e. "Unknown", blank) are skipped — only label the ones you have
verified ground truth for.

Run from the backend/ directory:

    venv\\Scripts\\python.exe evaluate.py
"""

import os
import re
import sys
import json
import time
from dataclasses import dataclass, asdict, field
from typing import Optional


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from ai_model.model import predict_image, AI_THRESHOLD


GROUND_TRUTH_FILE = os.path.join(PROJECT_ROOT, "Test", "README.md")
TEST_DIR = os.path.join(PROJECT_ROOT, "Test")
RESULTS_JSON = os.path.join(PROJECT_ROOT, "evaluation_results.json")
RESULTS_MD = os.path.join(PROJECT_ROOT, "evaluation_report.md")


@dataclass
class Result:
    filename: str
    true_label: str             # "ai" or "real"
    predicted_label: str        # "ai" or "real" (derived from ai_score vs AI_THRESHOLD)
    verbose_verdict: str        # the full TrueSight label
    ai_score: float
    deepfake_score: Optional[float] = None
    top_engine: Optional[str] = None
    correct: bool = False
    error: Optional[str] = None
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ground-truth parsing
# ---------------------------------------------------------------------------

_TABLE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|")


def parse_ground_truth(readme_path: str) -> dict[str, str]:
    """
    Extract {filename: "ai" | "real"} from Test/README.md.
    Skips rows whose Expected column doesn't start with "Real" or "AI".
    """
    truth: dict[str, str] = {}
    with open(readme_path, encoding="utf-8") as f:
        for line in f:
            m = _TABLE_ROW.match(line)
            if not m:
                continue
            fname = m.group(1).strip()
            expected = m.group(2).strip().lower()
            if expected.startswith("real"):
                truth[fname] = "real"
            elif expected.startswith("ai"):
                truth[fname] = "ai"
            # anything else (Unknown, blank) → skipped
    return truth


# ---------------------------------------------------------------------------
# Single-image evaluation
# ---------------------------------------------------------------------------

_ATTRIBUTION_KEY = re.compile(r"^Attribution \(([^)]+)\)$")


def evaluate_one(filename: str, true_label: str) -> Result:
    path = os.path.join(TEST_DIR, filename)
    if not os.path.exists(path):
        return Result(
            filename=filename, true_label=true_label,
            predicted_label="real", verbose_verdict="Error",
            ai_score=0.0, correct=False,
            error=f"File not found: {path}",
        )

    try:
        label, score, reasons, signals, _metadata = predict_image(path)
    except Exception as e:
        return Result(
            filename=filename, true_label=true_label,
            predicted_label="real", verbose_verdict="Error",
            ai_score=0.0, correct=False, error=str(e),
        )

    if label == "Error":
        return Result(
            filename=filename, true_label=true_label,
            predicted_label="real", verbose_verdict="Error",
            ai_score=0.0, correct=False, reasons=reasons,
            error="; ".join(reasons) if reasons else "predict_image returned Error",
        )

    predicted = "ai" if score >= AI_THRESHOLD else "real"

    # Pick the highest-scoring Hive attribution from the signals dict
    top_engine = None
    top_engine_score = -1.0
    for key, value in signals.items():
        m = _ATTRIBUTION_KEY.match(key)
        if m and value > top_engine_score:
            top_engine_score = value
            top_engine = m.group(1)

    return Result(
        filename=filename, true_label=true_label,
        predicted_label=predicted, verbose_verdict=label,
        ai_score=score,
        deepfake_score=signals.get("Sightengine Deepfake"),
        top_engine=top_engine,
        correct=(predicted == true_label),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------

def confusion_matrix(results: list[Result]) -> dict[str, int]:
    """Treat 'ai' as the positive class."""
    return {
        "tp": sum(1 for r in results if r.true_label == "ai" and r.predicted_label == "ai"),
        "fp": sum(1 for r in results if r.true_label == "real" and r.predicted_label == "ai"),
        "fn": sum(1 for r in results if r.true_label == "ai" and r.predicted_label == "real"),
        "tn": sum(1 for r in results if r.true_label == "real" and r.predicted_label == "real"),
    }


def metrics(cm: dict[str, int]) -> dict[str, float]:
    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def print_table(results: list[Result]) -> None:
    header = f"{'Filename':<55} {'Truth':<6} {'Pred':<6} {'Score':>7} {'OK':<6}"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda x: (x.true_label != "ai", -x.ai_score)):
        if r.error:
            marker, score_str = "ERR", "  n/a"
        else:
            marker = "ok" if r.correct else "WRONG"
            score_str = f"{r.ai_score:5.1f}%"
        print(f"{_truncate(r.filename, 55):<55} {r.true_label:<6} {r.predicted_label:<6} {score_str:>7} {marker:<6}")


def write_markdown_report(
    results: list[Result], cm: dict[str, int], m: dict[str, float], out_path: str
) -> None:
    valid = [r for r in results if not r.error]
    errors = [r for r in results if r.error]
    n_real = sum(1 for r in valid if r.true_label == "real")
    n_ai = sum(1 for r in valid if r.true_label == "ai")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# TrueSight Evaluation Report\n\n")
        f.write(f"_Generated by `backend/evaluate.py` on {time.strftime('%Y-%m-%d %H:%M')}._\n\n")

        f.write("## Methodology\n\n")
        f.write(
            "Each image in the `Test/` set with a verified ground-truth label (`Test/README.md` "
            "→ \"Expected\" column) was passed through the full TrueSight detection pipeline "
            "(`backend/ai_model/model.py::predict_image`). A prediction is classified as **AI** when "
            f"`ai_score >= {AI_THRESHOLD:.0f}%` and **real** otherwise. Sightengine provides the "
            "ai_score and deepfake score; Hive is consulted only when the image is flagged as AI, "
            "purely to extract per-engine attribution.\n\n"
        )

        f.write("## Sample composition\n\n")
        f.write(f"- Images evaluated: **{len(valid)}** (of {len(results)} candidates)\n")
        f.write(f"- Ground-truth real: **{n_real}**\n")
        f.write(f"- Ground-truth AI:   **{n_ai}**\n")
        f.write(f"- Errors / unrecoverable: **{len(errors)}**\n")
        f.write(f"- Binary classification threshold: `ai_score >= {AI_THRESHOLD:.0f}%`\n\n")

        f.write("## Confusion matrix\n\n")
        f.write("AI is the positive class.\n\n")
        f.write("|                | Predicted Real | Predicted AI |\n")
        f.write("| -------------- | -------------- | ------------ |\n")
        f.write(f"| **True Real**  | {cm['tn']} (TN)            | {cm['fp']} (FP)         |\n")
        f.write(f"| **True AI**    | {cm['fn']} (FN)            | {cm['tp']} (TP)         |\n\n")

        f.write("## Metrics\n\n")
        f.write("| Metric    | Value   | Interpretation |\n")
        f.write("| --------- | ------- | -------------- |\n")
        f.write(f"| Accuracy  | {m['accuracy']*100:5.1f}% | Overall correct fraction |\n")
        f.write(f"| Precision | {m['precision']*100:5.1f}% | When TrueSight says AI, how often it's right |\n")
        f.write(f"| Recall    | {m['recall']*100:5.1f}% | What fraction of all AI images TrueSight catches |\n")
        f.write(f"| F1        | {m['f1']*100:5.1f}% | Harmonic mean of precision and recall |\n\n")

        f.write("## Per-image breakdown\n\n")
        f.write("| Filename | True | Predicted | AI Score | Deepfake | Top Engine | Verdict | Correct |\n")
        f.write("| -------- | ---- | --------- | -------- | -------- | ---------- | ------- | ------- |\n")
        for r in sorted(results, key=lambda x: (x.true_label != "ai", -x.ai_score)):
            if r.error:
                df = eng = "—"
                ok = "⚠ error"
                score_str = "—"
                verdict = "Error"
            else:
                df = f"{r.deepfake_score:.1f}%" if r.deepfake_score is not None else "—"
                eng = r.top_engine or "—"
                ok = "✓" if r.correct else "✗"
                score_str = f"{r.ai_score:.1f}%"
                verdict = r.verbose_verdict
            f.write(
                f"| `{r.filename}` | {r.true_label} | {r.predicted_label} | "
                f"{score_str} | {df} | {eng} | {verdict} | {ok} |\n"
            )

        wrong = [r for r in valid if not r.correct]
        if wrong:
            f.write("\n## Failure analysis\n\n")
            f.write("Cases where TrueSight's verdict diverged from ground truth.\n\n")
            for r in wrong:
                kind = "false positive (real → AI)" if r.true_label == "real" else "false negative (AI → real)"
                f.write(f"### `{r.filename}` — {kind}\n\n")
                f.write(f"- AI score: **{r.ai_score:.1f}%**\n")
                if r.deepfake_score is not None:
                    f.write(f"- Deepfake score: {r.deepfake_score:.1f}%\n")
                if r.top_engine:
                    f.write(f"- Hive top engine: {r.top_engine}\n")
                if r.reasons:
                    f.write("- Reasons emitted by the pipeline:\n")
                    for reason in r.reasons:
                        f.write(f"  - {reason}\n")
                f.write("\n")

        if errors:
            f.write("## Errors\n\n")
            for r in errors:
                f.write(f"- `{r.filename}`: {r.error}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"ERROR: ground-truth file not found: {GROUND_TRUTH_FILE}")
        sys.exit(1)

    truth = parse_ground_truth(GROUND_TRUTH_FILE)
    if not truth:
        print(f"ERROR: no labelled rows found in {GROUND_TRUTH_FILE}.")
        print("Expected markdown rows like: | `filename.jpg` | Real | ... |")
        print("Rows with 'Unknown' in the Expected column are skipped.")
        sys.exit(1)

    n_ai = sum(1 for v in truth.values() if v == "ai")
    n_real = sum(1 for v in truth.values() if v == "real")

    print("--- TRUESIGHT EVALUATION HARNESS ---")
    print(f"Ground truth source: {GROUND_TRUTH_FILE}")
    print(f"Test directory:      {TEST_DIR}")
    print(f"Labelled images:     {len(truth)}  ({n_ai} AI, {n_real} real)")
    print(f"Estimated cost:      ~{len(truth) * 10} Sightengine ops + ~{n_ai} Hive calls")
    print("")
    print("Running predictions...")
    print("")

    results: list[Result] = []
    for i, (fname, label) in enumerate(sorted(truth.items()), 1):
        print(f"  [{i:>2}/{len(truth)}] {_truncate(fname, 55):<55} ", end="", flush=True)
        r = evaluate_one(fname, label)
        if r.error:
            print(f"ERROR: {_truncate(r.error, 60)}")
        else:
            tag = "ok " if r.correct else "WRONG"
            print(f"-> {r.predicted_label:<4} ({r.ai_score:5.1f}%)  [{tag}]")
        results.append(r)

    valid = [r for r in results if not r.error]
    cm = confusion_matrix(valid)
    m = metrics(cm)

    print("")
    print("--- PER-IMAGE TABLE ---")
    print_table(results)

    print("")
    print("--- CONFUSION MATRIX (AI = positive class) ---")
    print(f"                 Predicted Real    Predicted AI")
    print(f"  True Real      {cm['tn']:>14}   {cm['fp']:>14}")
    print(f"  True AI        {cm['fn']:>14}   {cm['tp']:>14}")
    print("")
    print("--- METRICS ---")
    print(f"  Accuracy:  {m['accuracy']*100:5.1f}%")
    print(f"  Precision: {m['precision']*100:5.1f}%   (TrueSight says AI -> right this often)")
    print(f"  Recall:    {m['recall']*100:5.1f}%   (this fraction of AI images caught)")
    print(f"  F1:        {m['f1']*100:5.1f}%")

    # Persist outputs
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_candidates": len(results),
                "valid": len(valid),
                "errors": len(results) - len(valid),
                "ai_threshold": AI_THRESHOLD,
                "confusion_matrix": cm,
                "metrics": m,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "results": [asdict(r) for r in results],
        }, f, indent=2, ensure_ascii=False)

    write_markdown_report(results, cm, m, RESULTS_MD)

    print("")
    print(f"Per-image JSON: {RESULTS_JSON}")
    print(f"Dissertation-ready Markdown: {RESULTS_MD}")


if __name__ == "__main__":
    main()
