# Contributing

Thanks for your interest in contributing. This is a hackathon project shared for learning, so the bar is pragmatic rather than bureaucratic.

## Project in one paragraph

The pipeline extracts structured damage facts from German workshop notes (Phase A, deterministic rules), reasons about repair, replace or assess per zone (Phase B, explicit rules plus DeepSeek with strict validation), and visualizes everything in a Next.js and React Three Fiber 3D viewer (Phase C). The authoritative system description is [presentation/presentation.md](presentation/presentation.md); read it before touching the pipeline.

## Ground rules

- **The German notes stay German.** Extraction logic operates on the German text. Don't translate or replace it.
- **Don't invent metrics.** Phase B has no official ground truth. Report what you changed and how you checked it, not a made-up accuracy.
- **Evidence over vibes.** Any LLM output must be validated against the source text. Follow the existing validator's patterns.
- **Small PRs.** One concern per PR. Extraction, reasoning, frontend and assets are separate layers with separate review surfaces.

## Setup

```bash
# Frontend (Next.js)
cd frontend
yarn
yarn dev            # http://localhost:8083

# Extraction pipeline (Python, uv)
cd extraction
uv sync
export DEEPSEEK_API_KEY=...   # only needed for LLM paths
```

## Workflow

1. Open an issue describing what you want to change and why (bug template / feature template available).
2. Fork the repo and create a branch off `main`, named like `fix/severity-boundary` or `feat/zone-calibration`.
3. Make your change, keeping it minimal and consistent with the surrounding code style.
4. Check your work (below), then open a pull request with the PR template filled in.
5. A maintainer reviews; expect questions about evidence and trade-offs. CI isn't configured, so the checklist below is the CI.

## Before you open a PR

**Any change:**

- [ ] `yarn build` in `frontend/` passes
- [ ] No secrets, credentials, or `.env` files committed
- [ ] No new dependency added without justification in the PR description

**Extraction or reasoning changes (`extraction/`):**

- [ ] `uv run python run_benchmark.py` runs and reported scores are included in the PR (before and after)
- [ ] New rules/prompts are covered by an example case in the PR description
- [ ] LLM paths still validate evidence against the original `freitext`

**Frontend changes (`frontend/`):**

- [ ] The viewer contract (`frontend/public/data/viewer_cases.json`) is rebuilt if fields changed (`frontend/scripts/build_viewer_cases.py`)
- [ ] Verified in a browser: dashboard plus at least one damage case (`/cases/case_850023` is a good test case)
- [ ] Screenshot attached for visual changes

**3D / asset changes:**

- [ ] Zone placement sanity-checked on all 5 archetypes
- [ ] GLBs stay normalized (`+x` front, wheels on z=0) and decimated (~5 MB)

## Commit & PR conventions

- Commit messages: short imperative summary, e.g. `Fix severity weighting for Hagelschaden`
- PR description: what, why, how it was tested, and what you deliberately did *not* do
- English for everything (code comments included); German only inside data/example text

## Where to help

Good starting points, roughly by increasing depth:

- **Frontend polish:** loading spinner for GLBs, mobile layout, accessibility pass, filter state persistence (see *Known limitations* in the README)
- **Extraction hardening:** out-of-distribution detection, fuzzy/character-level matching, regression suite
- **Zone calibration:** per-panel calibration of the 22-zone overlay against the real models
- **Evaluation:** a proper repair/replace ground-truth labelling workflow

## Questions

Open an issue. If it's about the reasoning layer, include the case id and the German note you're looking at.
