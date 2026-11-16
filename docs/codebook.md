# Codebook: Sentiment of User Messages

## Purpose
We score the sentiment of each user message in WildChat conversations to see how sentiment changes over turns.

## Data and unit of analysis
- **Data:** English WildChat conversations with 5–10 non-empty user messages (n = 538 conversations, 3,599 user messages).
- **Unit:** One user message. Each message is scored on its own, without the rest of the conversation.
- **Message length:** Every message is scored in full, including long messages.

## Coding target
Score **the tone the user expresses in this message**.

- Score the user's tone, not the topic of the message.
- Score what the text shows, not what the user might feel.
- Do not use your own opinion of the message.

## Scale

| Score | Label | Definition | Example |
|---|---|---|---|
| -2 | Strongly negative | Clear anger, insults, or a strong complaint. | "This is useless. You keep getting it wrong!" |
| -1 | Mildly negative | Mild dissatisfaction, criticism, or impatience. | "That's wrong." / "No, that's not what I asked." |
| 0 | Neutral | No clear emotion: a plain request, command, question, or pasted text or code. | "continue" / "Try again." / "Write an email to my professor." |
| +1 | Mildly positive | Polite language, approval, or mild satisfaction. | "Could you please write an email to my professor?" / "Thanks, that works." |
| +2 | Strongly positive | Clear praise, excitement, or strong thanks. | "Wow, this is perfect, thank you so much!" |

## Rules for unclear cases
1. **Negative topic, neutral tone → 0.** "Write a sad poem about losing a pet" is a request, not a negative message.
2. **Polite language → +1.** Words such as "please", "could you", "thank you", or "thanks in advance" make a message mildly positive, unless the message has a stronger tone elsewhere.
3. **Instructions to redo → 0; statements that the answer is wrong → -1.** "Try again" or "Do it one more time" is neutral. "That's wrong" or "This is not correct" shows mild dissatisfaction.
4. **Pasted text, code, or role-play lines → 0,** unless the user adds their own comment with clear tone.
5. **Mixed tone → the stronger tone.** If a message has both positive and negative tone, score the stronger one. If both are equally strong, score 0.
   - "Thanks, but this is completely useless!" → -2 (the negative tone is stronger)
   - "Thanks, but this is still wrong." → 0 (+1 and -1 are equally strong)
6. **Uncertain cases → flag for manual check.** If the score is unclear, give the best score and set `uncertain` to true. Team members review all flagged messages by hand.

## Target of negative tone
If the score is -1 or -2, also record what the negative tone is directed at:
- `ai`: the assistant or its answer ("Your answer is wrong." / "You keep making the same mistake.")
- `other`: something else, such as the user's own task, another person, or a situation ("My boss is so annoying.")

If the score is 0, +1, or +2, record `none`.

## Output format
For each message, return:
- `score`: one of -2, -1, 0, 1, 2
- `target`: ai, other, or none
- `uncertain`: true or false
- `reason`: one short sentence explaining the score

## Validation
1. Draw a random sample of 50 messages (seed = 42).
2. Two team members score them separately with this codebook.
3. Gemini scores the same 50 messages.
4. Compare the scores with `pd.crosstab`: human vs. human, and human vs. Gemini.
5. Read every disagreement. Decide whether a person misread the text, Gemini made a mistake, or the codebook is unclear. Revise the codebook if needed, then repeat.
6. Score all 3,599 messages only after the agreement is acceptable.
7. After scoring all messages, review every message with `uncertain = true` and record the final score.

## Version history
- v1: First version.
- v2: Polite language scored +1; "Try again" scored 0; uncertain cases flagged for manual check; long messages scored in full; added target of negative tone.