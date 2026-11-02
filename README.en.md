# gacha-planner

English | [简体中文](README.md)

An agent skill for resource planning and pull decisions in gacha games (miHoYo limited character and weapon banners). It provides executable, verifiable pull strategies under limited resources, maximizing goal-completion probability and overall account value.

## Features

- **Complete decision pipeline**: collect inputs → verify game info → build resource timeline → probability and risk analysis → compare plans → output actionable decisions.
- **Accurate probability modeling**: analytical and Monte Carlo methods covering soft pity, the guaranteed-pity system, multiple copies in one banner, and the stateful "Captured Radiance" mechanism in Genshin Impact.
- **Dual-perspective decisions**: hard pity gives the safety boundary; the statistical perspective (expected value, P50/P90/P95) gives the realistic outlook.
- **Non-pull acquisition**: decision rules for the persistent cultivation system and anniversary standard / limited five-star picks.
- **Weapon inventory and substitutes**: weapon-character fit analysis, free substitutes first, and allocation of limited weapons across characters.
- **Full-collection feasibility**: long-term income-vs-cost balance, per-patch and cumulative gaps.
- **Rerun wait quantification**: estimate first / second / third reruns and Chronicle Wish windows from historical rerun cadence.
- **Top-up gap filling**: combine top-up options by cost-per-pull from low to high.
- **Re-planning on deviation**: re-plan from the latest state after actual pull outcomes (lost or won the 50/50).

## Structure

```
gacha-planner/
├── SKILL.md                      # Core methodology and workflow
├── references/
│   ├── gacha-mechanics.md        # Fixed banner probabilities, pity, expectations, sources
│   ├── patch-income.md           # Per-patch income and full-collection long-term balance
│   ├── acquisition-methods.md    # Free pick decisions and rerun waiting
│   └── weapon-allocation.md      # Weapon fit, substitutes, allocation
└── scripts/
    └── pull_probability.py       # Probability, Monte Carlo, top-up, collection gap
```

## Workflow

1. **Collect inputs**: current resources and pity/guarantee state, future income, goal list (hard / flexible / optional), account status, plus special goals such as free picks and full collection.
2. **Verify game info**: banner timeline and source credibility tiers; fixed rules come from references.
3. **Build resource timeline**: rolling calculation at each banner closure; linear income assumption.
4. **Probability and risk analysis**: single/multi-target cost, dual perspectives, Captured Radiance, multiple copies, weapon pre-filtering.
5. **Generate and compare plans**: enumerate strategies, compare on a unified basis, trigger top-up when resources fall short.
6. **Output decisions**: priority ranking, actionable checklist, and conditional trigger rules.

## Core Principles

- Hard needs first; flexible goals only from the remainder.
- Value by irreplaceability; filling a team gap is worth more.
- Timing over totals; keep the two perspectives separate.
- Don't bet early on leaks; favor certain gains.
- Character and weapon pity are independent; keep separate ledgers.

## Use Cases

- Plan pulls under limited resources; decide whether to pull a limited character or weapon.
- Compare strategies; assess pity state and goal-completion probability.
- Plan cross-version resource allocation, or handle free picks, full collection, and rerun waits.

## License

[MIT](LICENSE)
