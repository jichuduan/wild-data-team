# Codebook v4: Sentiment of WildChat User Messages

## Purpose

Score the tone expressed in each user message to examine how it changes over the five user turns in a conversation.

## Data and unit of analysis

- **Source file:** `data/wildchat_cleaned_exactly5.json` in the `wild-data-team` repository.
- **Current file audit:** 432 conversations and 2,160 non-empty user messages; every conversation has exactly five user messages. These are the counts for the current exactly-five-turn file. Do not use the earlier figures of 538 conversations / 3,599 messages for this analysis.
- **Unit:** one user message, coded separately without assistant replies or other turns as sentiment context.
- **Turn:** user-message position 1–5 within a conversation.
- **Message length:** score the complete message. Pasted material, code, or fictional content does not count as the user's emotional tone unless the user adds their own clear affective comment.

## Language scope

The primary analysis is English-only. The dataset's conversation-level English label does not guarantee that every user message is English.

- If a message is primarily non-English, record its `message_id` and the reason in a language-exclusion log. Exclude it from the English-only sentiment analysis; do not assign neutral (0) simply because the codebook is in English.
- For mixed-language messages, include only when the user's expressed tone can be judged from the English portion. Otherwise log and exclude the message.
- Do not send excluded non-English messages to the English-only LLM analysis unless the team approves and documents a multilingual protocol.

## Coding target

Score **the tone the user expresses in this message**.

- Score the user's tone, not the topic of the message.
- Score what the text shows, not what the user might feel.
- Do not use your own opinion of the message.

## Scale

| Score | Label | Definition | Example |
|---|---|---|---|
| -2 | Strongly negative | Clear anger, insults, or a strong complaint. | “This is useless. You keep getting it wrong!” |
| -1 | Mildly negative | Mild dissatisfaction, criticism, or impatience. | “That's wrong.” / “No, that's not what I asked.” |
| 0 | Neutral | No clear emotion: a plain request, command, question, factual statement, or pasted text/code. | “Continue.” / “Try again.” / “Can you write a poem?” |
| +1 | Mildly positive | Explicit thanks, approval, or mild satisfaction. Politeness markers alone do not count as positive sentiment. | “Thanks, that works.” |
| +2 | Strongly positive | Clear praise, excitement, or emphatic thanks. | “Wow, this is perfect, thank you so much!” |

## Rules for unclear cases

1. **Negative topic, neutral tone → 0.** “Write a sad poem about losing a pet” is a request, not a negative message.
2. **Polite request language alone → 0.** “Can you,” “could you,” and “please” do not make a request positive. Example: “Could you write this, please?” → 0. Explicit thanks or approval can be +1: “Thanks, that works.” → +1.
3. **Redo instructions and factual status reports → 0 unless the user evaluates the result negatively.** “Try again,” “again,” and “Do it one more time” are neutral. A factual report such as “This line returns null” is also neutral by itself.
   - **Direct or indirect criticism of an answer, tool, or process → -1** when the user indicates it fails to meet a goal, even without anger or blame. Example: “The truncation only adds dots, but it needs to fit the container.” → -1 toward `ai`.
   - Directly saying the answer is wrong or expressing dissatisfaction that it still fails → -1 toward `ai`.
   - Clear anger, insult, or strong complaint → -2 toward `ai`.
4. **Pasted text, code, errors, or role-play → 0** unless the user adds their own comment with clear tone. Do not treat negative story events or error messages as the user's emotion.
5. **Mixed tone → the stronger tone.** If a message has both positive and negative tone, score the stronger one. If both are equally strong, score 0.
   - “Thanks, but this is completely useless!” → -2 (negative tone is stronger).
   - “Thanks, but this is still wrong.” → 0 (+1 and -1 are equally strong).
6. **Uncertain cases → flag for manual check.** Give the best score and set `uncertain` to true. Review flagged messages during adjudication. Language-scope exclusions are recorded separately and are not sentiment score 0.

## Target of negative tone

If the score is -1 or -2, record what the negative tone is directed at:

- `ai`: the assistant or its answer (“Your answer is wrong.” / “You keep making the same mistake.”)
- `other`: something else, such as the user's own task, another person, or a situation (“My boss is so annoying.”)

If the score is 0, +1, or +2, record `none`.

## Output format

For each in-scope English message, return:

- `score`: one of -2, -1, 0, 1, 2
- `target`: `ai`, `other`, or `none`
- `uncertain`: `true` or `false`
- `reason`: one short sentence explaining the score

For an out-of-scope language message, record the `message_id` and exclusion reason in the separate language-exclusion log; do not enter a sentiment score for the primary English-only analysis.

## Validation and adjudication

1. Select 50 user messages at random (seed = 42) from all eligible messages in the analysis file. Messages are sampled individually, so a conversation may contribute zero, one, or several messages.
2. Two human coders score the same sample independently with this codebook. They should not view or discuss each other's labels until both sheets are complete.
3. The LLM scores the same eligible English messages only after the human-only coding is complete and any data-use approval for external API processing is in place.
4. Report exact agreement, within-one-point agreement, Cohen's kappa, and quadratic weighted kappa for the two human coders before adjudication. Treat these as pilot estimates because the sample is small (50 messages).
5. Review every disagreement. Record both original scores, an adjudicated score, and a short reason. Update the codebook when disagreement reveals an unclear rule. Do not replace pre-adjudication reliability statistics with agreement after adjudication.
6. A provisional project criterion is quadratic weighted kappa >= .70. The team should also review every disagreement and decide whether the codebook is clear enough for full coding.
7. After the codebook is finalized, score the remaining in-scope messages in the current data file. Report the final analytic N after language exclusions; the source file contains 2,160 messages before those exclusions.
8. Review all `uncertain = true` cases and document final decisions.

## Ethics and privacy

WildChat contains real user messages and may include sensitive information, including medical or identifying details. Keep coding workbooks private, remove or redact direct identifiers, and do not send sensitive rows to an external API. Record excluded or redacted records by message ID without reproducing the sensitive text in shared reports.

## Version history

- v1: First version.
- v2: Polite language scored +1; “Try again” scored 0; uncertain cases flagged for manual check; long messages scored in full; added target of negative tone.
- v3: Added the adjudication rule that “Can you…” alone is neutral; continuing-error status reports without explicit dissatisfaction are neutral; clarified English-only exclusions; updated the sample and current dataset counts to the exactly-five-turn analysis file.
- v4: All politeness markers (“please,” “could you,” and “can you”) are neutral unless there is separate expressed positive affect; explicit thanks/approval may be +1. Indirect criticism that a response or process fails to meet a goal is -1.
