# AI usage

Space Apps asks teams to disclose where and how AI tools were used. Here is ours.

## Tools
- **Claude Code** (Anthropic), a coding assistant in the editor and terminal, running the **Claude Opus 5.5** and **Claude Sonnet 5.5** models.

## What the AI did
- Turned the team's written specification (problem, features, honesty rules, tech stack, phase plan) into an implementation plan and file structure.
- Wrote most of the code: the FastAPI backend, the rules engine, tests, the vanilla-JS frontend, the NASA DONKI proxy with caching, and the demo scenario.
- Wrote the first drafts of the action-protocol texts. These are marked **DRAFT, not medically reviewed** in every file and in the UI.
- Proposed candidate values for thresholds and "leads" (papers or standards to check). **Every value is marked `ASSUMPTION`, with an empty `source_url`,** until a team member checks it against a primary source. See [SOURCES.md](SOURCES.md).
- Ran the test suite and drove a headless browser to check the UI and take the screenshots in `docs/screenshots/`.
- Drafted this README, SOURCES.md generator and this file.

## What the team did
- Chose the challenge, wrote the product specification, the scientific-honesty rules, and the demo story.
- Reviewed and accepted the plan and every phase.
- Is responsible for verifying every threshold and source before any claim is made about medical validity.

## What the AI is NOT used for
- **No AI or machine learning runs inside CrewCheck.** All health assessments are transparent, rule-based logic (z-score vs. personal baseline + persistence rule). Every status shows the rule, the data, and the source that produced it.
