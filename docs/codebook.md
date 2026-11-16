# Codebook: Sentiment of User Messages

## Purpose
We score the sentiment of each user message in WildChat conversations to see how sentiment changes over turns.

## Data and unit of analysis
- **Data:** English WildChat conversations with 5–10 non-empty user messages (n = 538 conversations, 3,599 user messages).
- **Unit:** One user message. Each message is scored on its own, without the rest of the conversation.
- **Long messages:** Only the first 2,000 characters are scored. A column records which messages were cut.

## Coding target
Score **the tone the user expresses in this message**.

- Score the user's tone, not the topic of the message.
- Score what the text shows, not what the user might feel.
- Do not use your own opinion of the message.

## Scale

| Score | Label | Definition | Example |
|---|---|---|---|
| -2 | Strongly negative | Clear anger, insults, or a strong complaint. | "This is useless. You keep getting it wrong!" |
| -1 | Mildly negative | A correction, mild dissatisfaction, or impatience. | "No, that's not what I asked." |
| 0 | Neutral | No clear emotion: a plain request, command, question, or pasted text or code. | "continue" / "Write an email to my professor." |
| +1 | Mildly positive | Polite approval or mild satisfaction. | "Thanks, that works." |
| +2 | Strongly positive | Clear praise, excitement, or strong thanks. | "Wow, this is perfect, thank you so much!" |

## Rules for unclear cases
1. **Negative topic, neutral tone → 0.** "Write a sad poem about losing a pet" is a request, not a negative message.
2. **Politeness alone → 0.** "Please", "could you", or "thanks in advance" in a request does not make it positive.
3. **Corrections → -1.** "That's wrong" or "Try again" counts as mild dissatisfaction, even without emotional words.
4. **Pasted text, code, or role-play lines → 0,** unless the user adds their own comment with clear tone.
5. **Mixed tone → the stronger tone.** If both are equally strong, choose 0.
6. **Unsure between two scores → the one closer to 0.**

## Output format
For each message, return:
- `score`: one of -2, -1, 0, 1, 2
- `reason`: one short sentence explaining the score

## Validation
1. Draw a random sample of 50 messages (seed = 42).
2. Two team members score them separately with this codebook.
3. Gemini scores the same 50 messages.
4. Compare the scores with `pd.crosstab`: human vs. human, and human vs. Gemini.
5. Read every disagreement. Decide whether a person misread the text, Gemini made a mistake, or the codebook is unclear. Revise the codebook if needed, then repeat.
6. Score all 3,599 messages only after the agreement is acceptable.

## Version history
- v1 (2026-11-6): First version.