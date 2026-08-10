# forge-skill-evals

Evaluation framework, datasets, and results for [Forge SDLC](https://github.com/forge-sdlc/forge) skills.

## Structure

```
skills/
  generate-prd/
    dataset/cases/          # Input YAML + gold-standard PRDs
    criteria/               # Judge criteria YAML configs
    results/v3/             # Generated PRDs, traces, eval reports
reports/                    # HTML reports
```

## Tools

The test runner and evaluator live in the Forge repo:
- **PR:** [forge-sdlc/forge#297](https://github.com/forge-sdlc/forge/pull/297) (`devtools/test-skill/`)
- **Proposal:** [forge-sdlc/forge#296](https://github.com/forge-sdlc/forge/issues/296)

## Quick Start

```bash
# Clone this repo + Forge
git clone https://github.com/ItzikEzra-rh/forge-skill-evals.git
git clone https://github.com/forge-sdlc/forge.git
cd forge && git fetch origin pull/297/head:feat/test-skill && git checkout feat/test-skill

# Set API credentials
export ANTHROPIC_VERTEX_PROJECT_ID=your-project
export PYTHONPATH=/path/to/forge/src:$PYTHONPATH

# Run a single case
python3 devtools/test-skill/run.py \
  --skill generate-prd \
  --skill-dir /path/to/ai-skills/forge-skills/osac/generate-prd \
  --input ../forge-skill-evals/skills/generate-prd/dataset/cases/OSAC-2917/input.yaml \
  --output output/OSAC-2917/

# Evaluate against gold
python3 devtools/test-skill/evaluate.py \
  --criteria ../forge-skill-evals/skills/generate-prd/criteria/generate-prd.yaml \
  --generated output/OSAC-2917/enhancements/*/prd.md \
  --gold ../forge-skill-evals/skills/generate-prd/dataset/cases/OSAC-2917/gold-prd.md \
  --output output/OSAC-2917/eval-report/
```

## Related

- Skill fixes: [ItzikEzra-rh/ai-skills branch fix/forge-prd-skill-gaps-osac-3774](https://github.com/ItzikEzra-rh/ai-skills/commits/fix/forge-prd-skill-gaps-osac-3774)
- Jira: OSAC-3774
