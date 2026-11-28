# Sentiment in Five-Turn WildChat Conversations

## Research question and social-science relevance

**Research question:** In multi-turn user–ChatGPT conversations, does the tone expressed in user messages become more negative as the conversation proceeds? Is any change visible within the same conversation, or does it mainly reflect differences between conversations? What does a sentiment score capture: users' expressed message tone, or their attitude toward AI?

This question matters because repeated requests, corrections, and dissatisfaction can reveal friction in human–AI interaction. Measuring message tone can help identify where product support may be needed, while distinguishing tone from attitude prevents overstating what text sentiment can establish.

## Data, unit, provenance, and ethics

The data are from **WildChat-1M**, an openly released collection of ChatGPT conversations by AllenAI, accessed through the team's cleaned exactly-five-turn dataset in this repository (`data/wildchat_cleaned_exactly5.json`). The source is [AllenAI's WildChat-1M dataset on Hugging Face](https://huggingface.co/datasets/allenai/WildChat-1M).

The unit of analysis is **one user message**. Turn indicates the message's position (1–5) in a conversation. The final balanced English panel contains **316 conversations (1,580 messages)**, with five messages per conversation. Assistant replies were not included as scoring context. Gemini received each conversation's five user messages together in one request, labelled by turn, and was instructed to score each message on its own under Codebook v4.

WildChat contains real user text that may be sensitive. The team excluded one medically sensitive conversation before API scoring, removed two conversations after discovering Russian/mixed-language turns despite English metadata, and kept coder files and individual-level labels private. Three non-English/mixed turns were transmitted to Gemini before text screening caught the metadata issue; these turns and their conversations were then excluded from the English-only analysis. This is a limitation and is disclosed here. The repository includes the cleaned subset of the public WildChat-1M data used for analysis (`data/wildchat_cleaned_exactly5.json`); API outputs and individual-level labels are not shared.

## Method

Two human coders independently scored a 10-conversation pilot (all five user messages from each of 10 randomly selected conversations; 46 eligible messages after exclusions) using a five-point scale (−2 strongly negative to +2 strongly positive), then reviewed disagreements and finalized Codebook v4. The codebook scores the tone expressed in the message, not whether its topic is sad or whether the user is necessarily dissatisfied with AI. Requests and politeness markers such as “please” are neutral by themselves; explicit criticism of an answer or process can be negative.

Gemini 3.5 Flash Lite scored eligible user messages using the finalized codebook. Each request contained the five user messages from one conversation, and the prompt instructed the model to score each message on its own. Because the model could see the other turns, its scores may not be fully independent across turns. The main analysis compares mean score and the proportions of negative, neutral, and positive messages across turns 1–5. To separate within-conversation change from differences between conversations, the analysis also computes the paired difference **turn 5 minus turn 1** for each conversation and a bootstrap 95% interval for the mean paired difference.

For manual error analysis, the reviewer assessed all model non-neutral predictions plus five model-neutral messages per turn. This is a targeted audit designed to inspect likely errors and false negatives; it is not a probability sample of all messages.

## Initial and final findings

Mean tone scores by turn were:

| Turn | Mean score | Negative | Neutral | Positive |
|---:|---:|---:|---:|---:|
| 1 | −0.019 | 1.9% | 98.1% | 0.0% |
| 2 | −0.041 | 5.4% | 93.7% | 0.9% |
| 3 | −0.028 | 5.1% | 92.7% | 2.2% |
| 4 | −0.066 | 8.2% | 90.2% | 1.6% |
| 5 | −0.082 | 9.5% | 88.6% | 1.9% |

Across the same conversations, the average turn-5 minus turn-1 difference was **−0.063 points** (bootstrap 95% interval: **−0.108 to −0.019**). **278/316 (88.0%)** conversations had no score change; 29 (9.2%) were more negative at turn 5 and 9 (2.8%) were less negative. This suggests a small negative shift concentrated in a minority of conversations, rather than a broad decline across users. See `figure_turn_sentiment.svg` and the aggregate CSVs.

## Manual validation and error analysis

The two human coders' pre-adjudication exact agreement on the pilot was **86.96%** (Cohen's κ = **0.709**; quadratic weighted κ = **0.763**). After adjudication, Gemini matched all **46** eligible pilot labels (46/46). This is a small pilot, not proof of perfect general performance.

In the completed targeted blind-review queue, 140 in-scope messages had human labels. Exact score agreement was **99/140 (70.7%)**; full-label mismatches (score or target) were **43/140 (30.7%)**. Of 41 score disagreements, Gemini was more negative in 33 and more positive in 8. The most frequently recorded error type was indirect criticism (15 cases), followed by pasted text/role-play (8) and intensity errors (8). Among reviewed model-neutral cases, one was judged non-neutral. These results describe the deliberately enriched audit queue and must not be presented as overall population accuracy.

## Limitations and interpretation

- Sentiment scoring measures the tone of a message. It does **not** directly measure user attitude toward ChatGPT, satisfaction, or emotion outside the text.
- Messages were scored without assistant-response context. A short “No” or “again” can depend on the prior exchange, so message-level coding can miss conversational meaning.
- The final panel is English-only and restricted to exactly five user messages. It does not represent all WildChat users or conversation lengths.
- The manual error audit oversampled model non-neutral predictions, so its error proportions are not population estimates.
- LLM judgments can misread indirect criticism, pasted content, role-play, and emotional topic words. The pilot's perfect match should be interpreted cautiously alongside the lower agreement in the larger targeted review.
- Language metadata was imperfect; the three transmitted non-English/mixed turns were excluded from analysis after detection.

## Conclusion

In this balanced five-turn English sample, user-message tone became modestly more negative on average by turn five, but most conversations showed no change. The result is evidence about expressed message tone in this dataset, not a direct measure of user dissatisfaction with AI. The blind review indicates that careful interpretation and manual checks remain necessary, especially for indirect criticism and pasted or fictional text.

## Reproducibility note

The package includes the final codebook and API analysis script. The script requires a Gemini API key supplied locally through the `GEMINI_API_KEY` environment variable; never place that key in a shared file or repository. Aggregate tables in this package correspond to the text-screened panel described above. Raw API outputs and individual-level labels remain private.
