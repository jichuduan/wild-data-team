# Final Project: Measuring User Sentiment Analysis Across AI Conversations

This repository contains the code, codebook, and results for our COMPSS 211A
team project. We use Gemini to score the tone of user messages in five-turn
WildChat conversations and examine whether tone becomes more negative as
conversations continue. This README explains how to reproduce the analysis;
the project website presents the question, evidence, and limitations.

## Project overview

- **Research question:** In multi-turn user–ChatGPT conversations, does the tone expressed in user messages become more negative as the conversation proceeds?
- **Team members:** Yunzhi(Wendy) Zhang, Macy Chen, Wangmeiqi(Maggie) Wei, Jeannette Harris, Jichu Duan
- **Unit of analysis:** One user message; turn = its position (1–5) in a conversation.
- **Data source:** [WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) (AllenAI), English conversations with exactly five user messages.
- **Main result:** Mean tone became slightly more negative from turn 1 (−0.019) to turn 5 (−0.082); the paired turn-5 minus turn-1 difference was −0.063 (95% CI −0.108 to −0.019, N = 316 conversations). Most conversations (88%) showed no change.
- **Important limitation:** Scores measure the tone of message text, not users' attitude toward AI, and Gemini tended to score more negatively than human reviewers.

## Start here

One teammate creates the repository from this template with **Use this
template** on
[macss-berkeley/compss-211a-project-template](https://github.com/macss-berkeley/compss-211a-project-template),
then invites the other teammates as collaborators. The team should have only
one shared project repository.

Every teammate then:

1. accepts the GitHub invitation;
2. clones the repository with GitHub Desktop;
3. opens the complete repository folder in VS Code;
4. opens a terminal in that folder and runs:

   ```bash
   uv sync --frozen
   ```

5. selects the `.venv` environment as the Python interpreter and notebook
   kernel in VS Code.

Use `uv sync --frozen --all-groups` only if your project needs the larger NLP
packages used in the optional course materials. Ask the instructional team
before adding a package or changing the environment files.

## What goes where?

```text
.
├── README.md        project question, run order, and main findings
├── docs/            final project website published with GitHub Pages
├── notebooks/       exploration, analysis, figures, and explanations
├── scripts/         repeated tasks that should run the same way each time
├── data/            permitted small data files or data-access instructions
├── pyproject.toml   readable Python and package requirements
└── uv.lock          exact versions used by the team
```

### Start in a notebook

For most of this project, a notebook is the right place to work. Use a
notebook when you are:

- exploring unfamiliar data;
- trying a method for the first time;
- inspecting tables, plots, or individual texts;
- combining code, results, and written interpretation;
- preparing an analysis that a reader should follow step by step.

Give notebooks numbered names so their order is visible, for example:

```text
notebooks/01_explore_data.ipynb
notebooks/02_prepare_text.ipynb
notebooks/03_analyze_text.ipynb
notebooks/04_make_figures.ipynb
```

Not every project needs four notebooks. Use only the files that make your work
easier to understand.

### Move a repeated task into a script

A script is an ordinary Python file ending in `.py`. Create one when a step is
settled and you need to run it the same way more than once. Good candidates
include downloading data, cleaning raw files, or producing final tables and
figures.

For example:

```text
scripts/download_data.py
scripts/prepare_data.py
scripts/make_final_figures.py
```

Run a script from the repository folder:

```bash
uv run python scripts/prepare_data.py
```

Do not turn code into a script merely because it looks more professional. A
short, readable notebook is better than a script nobody on the team
understands. When you do create a script, first make the code work in a
notebook, simplify it, and make sure another teammate can explain what it does.

## Suggested project workflow

A simple notebook-first workflow is:

1. explore the data in `notebooks/01_explore_data.ipynb`;
2. document the data source and sharing limits below;
3. test cleaning and analysis steps in small notebook cells;
4. move only stable, repeated tasks into `scripts/`;
5. restart each important notebook and run it from top to bottom;
6. record the final run order in this README;
7. build the web report in `docs/index.md` from results you have verified.

### Current run order

1. Install the environment: `uv sync --frozen`
2. The cleaned data `data/wildchat_cleaned_exactly5.json` is included in this repository. To regenerate it, run `data/data_import_cleaning.ipynb` from top to bottom (about 2 hours because of API rate limits).
3. Set your Gemini API key in the terminal (never commit it): `export GEMINI_API_KEY="your-key"`
4. Create the human validation sample: select 10 conversations at random (seed 42) and include all five user messages from each (50 messages; 46 eligible after exclusions). Two coders score them independently and adjudicate disagreements.
5. Score all messages (requires the adjudicated validation file):
   ```
   uv run python scripts/llm_sentiment_analysis_v4.py --input data/wildchat_cleaned_exactly5.json --model gemini-3.5-flash-lite --all --validation-approved
   ```
   The team excluded one medically sensitive and two mixed-language conversations by row index (using `--exclude-conversation-index`).
6. Outputs are written to `llm_results/` (contains private files; do not commit). The aggregate results used in the report are `docs/turn_summary.csv` and `docs/assets/figure_turn_sentiment.svg`.

## Working together with GitHub

Do not do substantial project work directly on `main`. For each small task:

1. switch to `main` in GitHub Desktop and **Fetch origin**;
2. pull any new commits;
3. create a short branch named for the task, such as `document-data-source` or
   `add-first-figure`;
4. make one focused change;
5. inspect the changed files in GitHub Desktop;
6. commit with a message that describes the result;
7. publish the branch and open a pull request;
8. ask a teammate to review it;
9. merge only after the reviewer understands and approves the change;
10. switch back to `main` and pull the merged commit.

### Notebook rule

Only one person should edit a particular notebook at a time. Before editing:

- tell the team which notebook you are taking;
- pull the latest `main` and create a branch;
- keep the change focused and merge it promptly;
- restart the notebook and run all cells before requesting review;
- tell the team when the notebook is available again.

Notebook files contain code, prose, outputs, and metadata, so simultaneous
edits can produce conflicts that are hard to resolve safely. If a notebook
conflict occurs, work with the other author and rerun the final notebook. Do
not blindly choose “ours” or “theirs.”

## Team agreements

- **Who may merge pull requests?** Any teammate, after at least one other teammate has reviewed and approved the PR.
- **Where will the team record tasks?** WhatsApp Group Chat and Shared Google Docs.
- **How will the team review code it did not write?** The reviewer pulls the branch, runs the code locally, and comments on the PR before approving.

## Data and privacy

- **Source and access method:** WildChat-1M (public dataset on Hugging Face), downloaded through the Hugging Face datasets-server API in `data/data_import_cleaning.ipynb`.
- **Coverage:** 30,000 randomly sampled conversations (seed 42) -> 17,074 English -> 432 with exactly five user messages after de-duplication -> 316 in the final analysis after language and sensitivity exclusions.
- **What may be committed:** Code, the codebook, aggregate results (for example `docs/turn_summary.csv` and figures), and the cleaned subset `data/wildchat_cleaned_exactly5.json` drawn from the public WildChat-1M release.
- **What must stay outside GitHub:** API outputs and individual-level labels in `llm_results/`, manual coding files, and API keys.
- **How a new reader can obtain or reconstruct the data:** The cleaned data file is included in this repository. To rebuild it from the source, run `data/data_import_cleaning.ipynb` from top to bottom (about 2 hours because of API rate limits).

Never commit passwords, API keys, tokens, `.env` files, private data, or files
you do not have permission to share. The template ignores `data/raw/` and
`data/private/`, but a `.gitignore` rule is not a substitute for checking every
commit.

## Results and interpretation

- **Main finding:** Mean user-message tone fell from −0.019 at turn 1 to −0.082 at turn 5; the share of negative messages rose from 1.9% to 9.5%. Within the same conversations, the turn-5 minus turn-1 difference was −0.063 (bootstrap 95% CI −0.108 to −0.019).
- **Evidence:** `docs/turn_summary.csv`, `docs/assets/figure_turn_sentiment.svg`, and `docs/sentiment_methods/final_report.md`.
- **Validation:** Two human coders agreed exactly on 86.96% of the 46 eligible messages in a 10-conversation pilot (Cohen's κ = 0.709; quadratic weighted κ = 0.763). In a targeted review of 140 messages that oversampled likely errors, Gemini matched human scores in 70.7% of cases and was more negative in 33 of 41 disagreements.
- **Limitations:** English-only, exactly-five-turn sample; scores ignore assistant replies; Gemini's negative lean may exaggerate the trend.
- **Strongest claim supported:** In this sample, user-message tone became modestly more negative by turn five, driven by a minority of conversations (29 of 316).
- **Claim not supported:** That users become dissatisfied with AI as conversations continue, or that this pattern holds for all ChatGPT users or conversation lengths.

## Final project website

The website is your final written product and the surface your team will
present from. You do not need to write a separate report or create a separate
slide deck.

Start with `docs/index.md`. The template asks for:

- the research question and why it matters;
- the data source, unit of analysis, coverage, and ethical considerations;
- methods explained in clear language;
- findings supported by readable figures or tables;
- interpretation, limitations, and claims the evidence does not support;
- reproducibility information and a link to the repository;
- references.

This is a web report, not a web-design assignment. Use the provided Markdown
template and simple theme. You are graded on the quality of the research,
evidence, interpretation, reproducibility, and communication—not on custom
HTML, CSS, or JavaScript.

### Publish with GitHub Pages

1. Edit `docs/index.md` and save public-safe figures in `docs/assets/`.
2. Push the finished work to `main` through the normal branch and pull-request
   workflow.
3. On GitHub, open **Settings → Pages**.
4. Choose **Deploy from a branch**, select `main`, and select the `/docs`
   folder.
5. Open the published URL and check every section, image, and link.

GitHub Pages sites are public. Do not publish restricted data, identifying
information, credentials, or material you do not have permission to share.
If the topic or data cannot be discussed safely on a public page, contact the
instructional team early for a sanitized or offline alternative.

Before presenting, print or export the website to PDF. This is only an
archival copy and offline backup; it is not a separate report.

## Before submitting

- [ ] Every teammate can clone and open the repository.
- [ ] `uv sync --frozen` creates the supported environment.
- [ ] The README gives the actual run order.
- [ ] Important notebooks run from top to bottom in a fresh kernel.
- [ ] Scripts can be run from the repository folder with their documented
      command.
- [ ] The website includes the required research, evidence, interpretation,
      limitation, reproducibility, and reference sections.
- [ ] Figures and reported values match the notebooks and scripts.
- [ ] The GitHub Pages URL works in a signed-out browser.
- [ ] A PDF snapshot of the website is ready as a presentation backup.
- [ ] The data source, exclusions, and sharing limits are documented.
- [ ] No credentials, restricted data, or accidental large files are present.
- [ ] The final contribution of each team member is recorded.
