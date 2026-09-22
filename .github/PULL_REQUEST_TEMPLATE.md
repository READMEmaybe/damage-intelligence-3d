## What

<!-- One or two sentences: what does this change? -->

## Why

<!-- What problem does it solve? Link the issue if there is one: Closes #123 -->

## How it was tested

<!--
- Extraction/reasoning: benchmark before and after (run_benchmark.py output)
- Frontend: browser check + screenshot for visual changes
- 3D/assets: zone sanity check on which archetypes?
-->

## Checklist

- [ ] `yarn build` passes in `frontend/`
- [ ] No secrets / env files committed
- [ ] No new dependency without justification
- [ ] Benchmark scores (before and after) included, if `extraction/` changed
- [ ] `viewer_cases.json` rebuilt, if the viewer contract changed
- [ ] The German source text is unmodified
