# Routing Experiments

This folder aggregates experiment outputs and summaries for the routing optimization project.

## Baseline vs Standard vs Robust
- Runner: `experiments/routing/baseline_comparison.py`
- Data: built-in mock demand with predictive features and quantile columns
- Metrics: total distance (km), route count, SLA violations, computation time (s)

## How to run
```bash
cd routing_optimization
python experiments/routing/baseline_comparison.py
```

## Expected output (sample)
- Greedy baseline: ~0.15 km, 1 route, 0 SLA violations
- Standard OR-Tools: ~0.12 km, 1 route, 0 SLA violations
- Robust (6 scenarios): ~0.12 km worst-case, 1 route, 0 SLA violations

## Next steps
- Persist experiment results to JSON/CSV for reproducible reports
- Add plots comparing distance and runtime across scenarios
- Tune OR-Tools strategies via `config.py` (first solution, metaheuristic, time limit)
