"""Gemini sentiment workflow following the project's GitHub codebook.

Validation phase: uv run python scripts/llm_sentiment_analysis.py --input .\data\wildchat_cleaned_exactly5.json --output-dir .\llm_results --model YOUR_GEMINI_MODEL --validation-only
Full run (after two-human validation is adjudicated and approved): same command with --all --validation-approved

Requires GEMINI_API_KEY in the environment. The script sends redacted English
user messages to Gemini. Review privacy requirements; never commit secrets or raw text.
"""

import argparse
import csv
import json
import os
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


SEED = 42
PROMPT_VERSION = "github_codebook_v4"
SCORES = (-2, -1, 0, 1, 2)


class TurnLabel(BaseModel):
    turn: int = Field(description="User-message position in the conversation, from 1 to 5")
    score: Literal[-2, -1, 0, 1, 2]
    target: Literal["ai", "other", "none"]
    uncertain: bool
    reason: str = Field(description="One short sentence explaining the score")


class ConversationLabels(BaseModel):
    turns: list[TurnLabel]


SYSTEM_PROMPT = """Follow this sentiment codebook exactly. Score the tone the user expresses in each message, not the topic and not what you think the user might feel. Score each message independently and in full; do not use the other messages in the same conversation to reinterpret it.
Return one result for every supplied user message, preserving the turn number.

Score scale: -2 = clear anger, insults, or strong complaint; -1 = mild dissatisfaction, direct or indirect criticism, or impatience; 0 = no clear emotion, including a plain request, command, question, pasted text/code, or role-play line; +1 = explicit thanks, approval, or mild satisfaction; +2 = clear praise, excitement, or emphatic thanks.

Rules: a negative topic with neutral wording is 0. Politeness markers alone, including 'please', 'could you', and 'can you', are neutral (0); they do not express positive sentiment by themselves. Explicit thanks or approval may be +1. A direct or indirect critique that an answer, tool, or process fails to meet a stated goal is mildly negative (-1), even without anger or blame. A factual status report with no evaluation is 0. A request to redo/continue is 0. Pasted text, code, or role-play is 0 unless the user adds their own clear-toned comment. For mixed tone use the stronger tone; if positive and negative are equally strong, use 0. If genuinely uncertain, give the best score and set uncertain=true; otherwise false.

Target: for scores -1/-2 choose ai when the negative tone targets the assistant or its answer; choose other when it targets another person, situation, or the user's own task. For scores 0/+1/+2 target must be none. Give one short sentence as reason. Do not include extra fields."""


def extract_five_user_messages(row: dict) -> list[dict]:
    """Return the five user-message turns and their dataset language labels."""
    messages = []
    for utterance in row.get("conversation") or []:
        if utterance.get("role") != "user":
            continue
        content = utterance.get("content")
        if isinstance(content, str) and content.strip():
            messages.append({"text": content.strip(), "language": utterance.get("language") or "Unknown"})
    return messages


def redact_obvious_identifiers(text: str) -> str:
    """Basic safeguards only; this is not comprehensive de-identification."""
    text = re.sub(r"(?i)\bsk-(?:proj|live)-[A-Za-z0-9_-]{8,}\b", "[REDACTED_KEY]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = re.sub(r"https?://\S+", "[URL]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)", "[REDACTED_NUMBER]", text)
    text = re.sub(r"\b[A-Fa-f0-9]{24,}\b", "[REDACTED_ID]", text)
    return text


def score_conversation(client, model: str, messages: list[dict]) -> list[dict]:
    payload = [{"turn": i, "user_message": redact_obvious_identifiers(message["text"])}
               for i, message in enumerate(messages, start=1)]
    prompt = SYSTEM_PROMPT + "\n\nMessages to score independently:\n" + json.dumps(payload, ensure_ascii=False)
    response = client.interactions.create(
        model=model,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ConversationLabels.model_json_schema(),
        },
    )
    parsed = ConversationLabels.model_validate_json(response.output_text)
    if len(parsed.turns) != len(payload):
        raise ValueError("Model did not return exactly one structured label per supplied turn")
    results = [turn.model_dump() for turn in parsed.turns]
    expected_turns = list(range(1, len(payload) + 1))
    if [x["turn"] for x in results] != expected_turns:
        raise ValueError("Model returned turn numbers out of order")
    for result in results:
        if result["score"] < 0 and result["target"] == "none":
            raise ValueError("Negative score requires target='ai' or target='other'")
        if result["score"] >= 0 and result["target"] != "none":
            raise ValueError("Nonnegative score requires target='none'")
    for i, result in enumerate(results):
        result["language"] = messages[i]["language"]
    return results


def bootstrap_ci(values: list[float], reps: int = 4000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(SEED)
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return [samples[int(.025 * reps)], samples[int(.975 * reps)]]


def read_validation_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_validation_rows(path: Path, rows: list[dict]) -> None:
    fields = ["validation_id", "conversation_index", "turn", "gemini_score", "gemini_target",
              "gemini_uncertain", "gemini_reason", "human_a_score", "human_a_target", "human_a_uncertain",
              "human_a_reason", "human_b_score", "human_b_target", "human_b_uncertain", "human_b_reason",
              "disagreement_reviewed", "adjudicated_final_score", "error_type", "notes", "text_PRIVATE"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def get_or_create_validation_sample(eligible: list[tuple[int, list[dict]]], path: Path) -> list[dict]:
    if path.exists():
        return read_validation_rows(path)
    candidates = []
    for conversation_index, messages in eligible:
        for turn, message in enumerate(messages, start=1):
            candidates.append({"conversation_index": conversation_index, "turn": turn,
                               "text_PRIVATE": message["text"]})
    rng = random.Random(42)
    sample = rng.sample(candidates, min(50, len(candidates)))
    rows = []
    for validation_id, item in enumerate(sample, start=1):
        rows.append({"validation_id": validation_id, **item, "gemini_score": "", "gemini_target": "",
                     "gemini_uncertain": "", "gemini_reason": "", "human_a_score": "",
                     "human_a_target": "", "human_a_uncertain": "", "human_a_reason": "",
                     "human_b_score": "", "human_b_target": "", "human_b_uncertain": "",
                     "human_b_reason": "", "disagreement_reviewed": "", "adjudicated_final_score": "",
                     "error_type": "", "notes": ""})
    write_validation_rows(path, rows)
    return rows


def validation_statistics(rows: list[dict]) -> dict | None:
    import pandas as pd
    from sklearn.metrics import cohen_kappa_score

    complete = []
    complete_source_rows = []
    for row in rows:
        try:
            complete.append({
                "human_a": int(row["human_a_score"]),
                "human_b": int(row["human_b_score"]),
                "gemini": int(row["gemini_score"]),
            })
            complete_source_rows.append(row)
        except (ValueError, TypeError, KeyError):
            continue
    if not complete:
        return None

    def compare(first: str, second: str) -> dict:
        pairs = [(r[first], r[second]) for r in complete]
        table = pd.crosstab(pd.Series([a for a, _ in pairs], name=first),
                            pd.Series([b for _, b in pairs], name=second))
        table = table.reindex(index=SCORES, columns=SCORES, fill_value=0)
        return {
            "n_paired": len(pairs),
            "exact_agreement": sum(a == b for a, b in pairs) / len(pairs),
            "cohen_kappa": cohen_kappa_score([a for a, _ in pairs], [b for _, b in pairs], labels=list(SCORES)),
            "crosstab_rows_first_columns_second": table.to_dict(),
        }

    disagreement_rows = [row for row, labels in zip(complete_source_rows, complete)
                         if len({labels["human_a"], labels["human_b"], labels["gemini"]}) > 1]
    error_types = Counter(str(r.get("error_type", "")).strip() for r in disagreement_rows
                          if str(r.get("error_type", "")).strip())
    return {
        "n_messages_with_all_three_scores": len(complete),
        "human_a_vs_human_b": compare("human_a", "human_b"),
        "human_a_vs_gemini": compare("human_a", "gemini"),
        "human_b_vs_gemini": compare("human_b", "gemini"),
        "disagreement_n": len(disagreement_rows),
        "disagreement_validation_ids": [r.get("validation_id") for r in disagreement_rows],
        "reviewed_disagreement_n": sum(str(r.get("disagreement_reviewed", "")).lower() == "true" for r in disagreement_rows),
        "error_type_counts_from_reviewed_rows": dict(error_types),
        "uncertain_counts": {
            "human_a": sum(str(r.get("human_a_uncertain", "")).lower() == "true" for r in rows),
            "human_b": sum(str(r.get("human_b_uncertain", "")).lower() == "true" for r in rows),
            "gemini": sum(str(r.get("gemini_uncertain", "")).lower() == "true" for r in rows),
        },
    }


def verify_validation_approval(path: Path, explicitly_approved: bool) -> None:
    if not explicitly_approved:
        raise ValueError("Full scoring is gated: review validation disagreements and pass --validation-approved after the team accepts the codebook/model agreement.")
    if not path.exists():
        raise ValueError("Run and complete the 46-message eligible pilot validation before full scoring.")
    rows = read_validation_rows(path)
    if len(rows) != 46:
        raise ValueError(f"Expected 46 eligible pilot validation messages; found {len(rows)}.")
    for row in rows:
        try:
            human_a, human_b, gemini = int(row["human_a_score"]), int(row["human_b_score"]), int(row["gemini_score"])
        except (ValueError, TypeError, KeyError):
            raise ValueError("Fill both human scores and Gemini scores for all 50 messages before full scoring.")
        if any(score not in SCORES for score in (human_a, human_b, gemini)):
            raise ValueError("Validation scores must be one of -2, -1, 0, 1, 2.")
        if len({human_a, human_b, gemini}) > 1 and str(row.get("disagreement_reviewed", "")).lower() != "true":
            raise ValueError("Mark disagreement_reviewed=true for every row where human/Gemini scores disagree before full scoring.")
        if len({human_a, human_b, gemini}) > 1:
            try:
                adjudicated = int(row["adjudicated_final_score"])
            except (ValueError, TypeError, KeyError):
                raise ValueError("Enter adjudicated_final_score for every validation disagreement before full scoring.")
            if adjudicated not in SCORES:
                raise ValueError("Adjudicated final score must be one of -2, -1, 0, 1, 2.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="llm_results")
    parser.add_argument("--model", required=True, help="Model ID enabled for your API project")
    size = parser.add_mutually_exclusive_group(required=True)
    size.add_argument("--validation-only", action="store_true", help="Score the codebook's random validation sample")
    size.add_argument("--all", action="store_true", help="Score all English messages after validation approval")
    parser.add_argument("--validation-approved", action="store_true", help="Team has reviewed all disagreements and accepted the method")
    parser.add_argument("--exclude-conversation-index", type=int, action="append", default=[],
                        help="Exclude a sensitive conversation by zero-based source row index; may repeat")
    parser.add_argument("--pause-seconds", type=float, default=0.2)
    args = parser.parse_args()

    input_path, out_dir = Path(args.input), Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as f:
        conversations = json.load(f)

    # Step 1: use only conversations with exactly five non-empty user messages
    # and English tags on all five messages, matching the GitHub codebook.
    eligible = []
    invalid_rows = 0
    sequence_mismatches = 0
    nonenglish_rows = 0
    sensitive_conversations_excluded = 0
    for conversation_index, row in enumerate(conversations):
        if conversation_index in args.exclude_conversation_index:
            sensitive_conversations_excluded += 1
            continue
        user_messages = extract_five_user_messages(row)
        stored_messages = row.get("user_messages") or []
        if [m["text"] for m in user_messages] != stored_messages:
            sequence_mismatches += 1
        if len(user_messages) != 5 or len(stored_messages) != 5:
            invalid_rows += 1
            continue
        if not all(message["language"] == "English" for message in user_messages):
            nonenglish_rows += 1
            continue
        eligible.append((conversation_index, user_messages))
    eligible_total = len(eligible)
    language_counts_all = Counter(m["language"] for _, msgs in eligible for m in msgs)
    validation_path = out_dir / "manual_validation_PRIVATE.csv"

    # Codebook order: first compare two humans with Gemini on the same random
    # 50-message sample. Only after the team adjudicates it may --all proceed.
    if args.validation_only:
        validation_rows = get_or_create_validation_sample(eligible, validation_path)
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            print(f"Validation template created: {validation_path.resolve()}")
            print("Set GEMINI_API_KEY locally, then rerun --validation-only. Do not paste the key into chat.")
            return
        client = genai.Client()
        failures = []
        for row in validation_rows:
            if str(row.get("gemini_score", "")).strip():
                continue
            last_error = None
            message = {"text": row["text_PRIVATE"], "language": "English"}
            for attempt in range(5):
                try:
                    result = score_conversation(client, args.model, [message])[0]
                    row["gemini_score"] = result["score"]
                    row["gemini_target"] = result["target"]
                    row["gemini_uncertain"] = result["uncertain"]
                    row["gemini_reason"] = result["reason"]
                    write_validation_rows(validation_path, validation_rows)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = str(exc)
                    time.sleep(min(2 ** attempt, 20))
            if last_error:
                failures.append({"validation_id": row["validation_id"], "error": last_error})
            time.sleep(args.pause_seconds)
        stats = validation_statistics(validation_rows)
        validation_result = {
            "sample_n": len(validation_rows),
            "sample_seed": 42,
            "gemini_scored_n": sum(bool(str(r.get("gemini_score", "")).strip()) for r in validation_rows),
            "human_a_scored_n": sum(bool(str(r.get("human_a_score", "")).strip()) for r in validation_rows),
            "human_b_scored_n": sum(bool(str(r.get("human_b_score", "")).strip()) for r in validation_rows),
            "api_failures": failures,
            "agreement": stats,
            "note": "Two human scores are required; review every disagreement and uncertain message before full scoring.",
        }
        (out_dir / "manual_validation_results.json").write_text(json.dumps(validation_result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(validation_result, ensure_ascii=False, indent=2))
        print(f"Private annotation sheet: {validation_path.resolve()}")
        return

    verify_validation_approval(validation_path, args.validation_approved)

    # Step 2: call the LLM once per conversation (five messages in, five labels out).
    # Checkpoint only the classifications; do not persist raw prompts in the cache.
    cache_path = out_dir / f"scores_{re.sub(r'[^A-Za-z0-9_.-]', '_', args.model)}_{PROMPT_VERSION}.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                cache[int(record["conversation_index"])] = record["turns"]

    client = genai.Client()
    failures = []
    newly_scored = []
    for conversation_index, messages in eligible:
        if conversation_index in cache:
            continue
        last_error = None
        for attempt in range(5):
            try:
                labels = score_conversation(client, args.model, messages)
                record = {"conversation_index": conversation_index, "turns": labels}
                with cache_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                cache[conversation_index] = labels
                newly_scored.append(conversation_index)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                time.sleep(min(2 ** attempt, 20))
        if last_error:
            failures.append({"conversation_index": conversation_index, "error": last_error})
        time.sleep(args.pause_seconds)

    # Step 3: prepare aligned repeated-turn data from successful calls.
    eligible_by_id = dict(eligible)
    rows = []
    for conversation_index, _ in eligible:
        if conversation_index not in cache:
            continue
        messages = eligible_by_id[conversation_index]
        for result in cache[conversation_index]:
            turn = int(result["turn"])
            rows.append({
                "conversation_index": conversation_index,
                **result,
                "text": messages[turn - 1]["text"],
            })

    # Step 4: calculate turn 1-5 trajectory and paired first-vs-fifth difference.
    by_turn = defaultdict(list)
    chats = defaultdict(dict)
    for row in rows:
        by_turn[row["turn"]].append(row)
        chats[row["conversation_index"]][row["turn"]] = row
    turn_summary = {}
    for turn in range(1, 6):
        values = [int(r["score"]) for r in by_turn[turn]]
        if values:
            turn_summary[str(turn)] = {
                "n_conversations": len(values),
                "mean_score": statistics.mean(values),
                "share_score_negative": sum(v < 0 for v in values) / len(values),
                "share_score_neutral": sum(v == 0 for v in values) / len(values),
                "share_score_positive": sum(v > 0 for v in values) / len(values),
                "uncertain_count": sum(bool(r["uncertain"]) for r in by_turn[turn]),
            }
    complete_chats = [c for c in chats.values() if all(t in c for t in range(1, 6))]
    deltas = [int(c[5]["score"]) - int(c[1]["score"]) for c in complete_chats]
    paired = {
        "n_complete_conversations": len(complete_chats),
        "mean_turn1_score": statistics.mean(int(c[1]["score"]) for c in complete_chats) if complete_chats else None,
        "mean_turn5_score": statistics.mean(int(c[5]["score"]) for c in complete_chats) if complete_chats else None,
        "mean_turn5_minus_turn1": statistics.mean(deltas) if deltas else None,
        "bootstrap_95_ci_delta": bootstrap_ci(deltas),
        "share_turn5_more_negative": sum(d < 0 for d in deltas) / len(deltas) if deltas else None,
        "share_turn5_less_negative": sum(d > 0 for d in deltas) / len(deltas) if deltas else None,
        "share_no_change": sum(d == 0 for d in deltas) / len(deltas) if deltas else None,
    }

    # Step 5: save structured labels and aggregates. Raw texts go only into the
    # explicitly private review template; aggregate files do not contain text.
    summary = {
        "input_file": str(input_path.resolve()),
        "model": args.model,
        "prompt_version": PROMPT_VERSION,
        "eligible_exactly_five_turn_conversations": eligible_total,
        "conversations_selected_for_this_run": len(eligible),
        "conversations_scored_successfully": len(chats),
        "invalid_not_exactly_five_rows_excluded": invalid_rows,
        "rows_excluded_because_not_all_five_messages_are_english": nonenglish_rows,
        "sensitive_conversations_excluded_by_index": sensitive_conversations_excluded,
        "english_user_messages_scored": len(rows),
        "stored_vs_extracted_user_message_sequence_mismatches": sequence_mismatches,
        "language_tags_observed_in_eligible_data": dict(language_counts_all),
        "api_failures": failures,
        "validation_approval": "Two-human validation was completed and approved before full scoring.",
        "turn_summary": turn_summary,
        "paired_turn1_turn5": paired,
        "design": "Balanced panel: retain only conversations with exactly five non-empty user messages and English language labels on all five; each message is scored independently using the GitHub codebook.",
        "api_calls_new_this_run": len(newly_scored),
        "random_seed": SEED,
    }
    (out_dir / "llm_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "llm_api_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "turn_labels_PRIVATE.csv").open("w", encoding="utf-8-sig", newline="") as f:
        import csv
        fields = ["conversation_index", "turn", "language", "score", "target", "uncertain", "reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})

    validation_result_path = out_dir / "manual_validation_results.json"
    if validation_result_path.exists():
        summary["manual_validation"] = json.loads(validation_result_path.read_text(encoding="utf-8"))
    (out_dir / "llm_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Create a private queue for codebook-required review of every uncertain
    # full-sample Gemini score; the human final score is filled by the team.
    uncertain_path = out_dir / "uncertain_scores_PRIVATE.csv"
    uncertain_rows = [r for r in rows if bool(r["uncertain"])]
    if uncertain_rows and not uncertain_path.exists():
        with uncertain_path.open("w", encoding="utf-8-sig", newline="") as f:
            fields = ["conversation_index", "turn", "gemini_score", "gemini_target", "gemini_reason",
                      "human_final_score", "review_notes", "text_PRIVATE"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in uncertain_rows:
                writer.writerow({"conversation_index": row["conversation_index"], "turn": row["turn"],
                                 "gemini_score": row["score"], "gemini_target": row["target"],
                                 "gemini_reason": row["reason"], "human_final_score": "",
                                 "review_notes": "", "text_PRIVATE": row["text"]})

    # Step 7: save visualization for the balanced 1-to-5 trajectory.
    if turn_summary:
        import matplotlib.pyplot as plt
        x = [int(k) for k in turn_summary]
        y = [turn_summary[str(t)]["mean_score"] for t in x]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(x, y, marker="o", color="#147D80", linewidth=2)
        ax.axhline(0, color="#777777", linestyle="--", linewidth=1)
        ax.set(xticks=range(1, 6), xlabel="User-message position",
               ylabel="Gemini codebook score (-2 to +2)", title="User message sentiment across five turns")
        fig.tight_layout()
        fig.savefig(out_dir / "llm_tone_turns.png", dpi=180)
        plt.close(fig)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nResults: {out_dir.resolve()}")
    print("Keep *_PRIVATE.csv and the score cache private; they can contain personal text or linkage IDs.")


if __name__ == "__main__":
    main()
