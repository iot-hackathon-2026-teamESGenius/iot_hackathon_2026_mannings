"""
Scenario generator for predictive demand with quantiles and learning feature.
"""

from typing import Dict, List, Optional
import copy
import numpy as np


class ScenarioGenerator:
    """Build demand scenarios from quantiles or ratio fallback."""

    def __init__(
        self,
        quantile_keys: Optional[Dict[str, str]] = None,
        feature_key: Optional[str] = None,
        feature_weight: float = 0.0,
        scenario_weights: Optional[List[float]] = None,
        monte_carlo_samples: int = 0,
        monte_carlo_std: float = 0.05,
        monte_carlo_max_samples: int = 20,
    ) -> None:
        self.quantile_keys = quantile_keys or {}
        self.feature_key = feature_key
        self.feature_weight = feature_weight
        self.scenario_weights = scenario_weights
        self.monte_carlo_samples = monte_carlo_samples
        self.monte_carlo_std = monte_carlo_std
        self.monte_carlo_max_samples = monte_carlo_max_samples

    def _apply_feature(self, demand: float, store: Dict) -> float:
        if self.feature_key and self.feature_weight != 0 and self.feature_key in store:
            feature_val = float(store[self.feature_key])
            scale = 1 + self.feature_weight * (feature_val - 0.5)
            scale = min(max(scale, 0.8), 1.2)  # clip to avoid extreme swings
            demand *= scale
        return max(demand, 0)

    def _has_quantiles(self, store: Dict) -> bool:
        required = [k for k in self.quantile_keys.values() if k]
        return all(k in store for k in required) if required else False

    def _quantile_scenarios(self, base_vrp_input: Dict) -> List[Dict]:
        scenarios: List[Dict] = []
        scenario_defs = [
            ("low", self.quantile_keys.get("low")),
            ("mid", self.quantile_keys.get("mid")),
            ("high", self.quantile_keys.get("high")),
        ]
        for name, key in scenario_defs:
            if not key:
                continue
            scenario_input = copy.deepcopy(base_vrp_input)
            for store in scenario_input["stores"]:
                base_demand = float(store.get(key, store.get("demand", 0)))
                store["demand"] = self._apply_feature(base_demand, store)
            scenario_input["scenario_name"] = name
            scenario_input["scenario_ratio"] = None
            scenarios.append(scenario_input)
        return scenarios

    def _ratio_scenarios(self, base_vrp_input: Dict, demand_ratios: List[float]) -> List[Dict]:
        scenarios: List[Dict] = []
        for idx, ratio in enumerate(demand_ratios):
            scenario_input = copy.deepcopy(base_vrp_input)
            for store in scenario_input["stores"]:
                base_demand = float(store.get("demand", 0)) * ratio
                store["demand"] = self._apply_feature(base_demand, store)
            scenario_input["scenario_name"] = f"ratio_{ratio:.2f}"
            scenario_input["scenario_ratio"] = ratio
            if self.scenario_weights and len(self.scenario_weights) == len(demand_ratios):
                scenario_input["scenario_weight"] = float(self.scenario_weights[idx])
            scenarios.append(scenario_input)
        return scenarios

    def _monte_carlo_scenarios(self, base_vrp_input: Dict) -> List[Dict]:
        scenarios: List[Dict] = []
        if self.monte_carlo_samples <= 0:
            return scenarios

        num_samples = min(self.monte_carlo_samples, self.monte_carlo_max_samples)
        for i in range(num_samples):
            ratio = float(np.random.normal(1.0, self.monte_carlo_std))
            ratio = float(min(max(ratio, 0.8), 1.2))  # clamp to reasonable band
            scenario_input = copy.deepcopy(base_vrp_input)
            for store in scenario_input["stores"]:
                base_demand = float(store.get("demand", 0)) * ratio
                store["demand"] = self._apply_feature(base_demand, store)
            scenario_input["scenario_name"] = f"mc_{i+1}"
            scenario_input["scenario_ratio"] = ratio
            scenarios.append(scenario_input)
        return scenarios

    def generate(self, base_vrp_input: Dict, demand_ratios: List[float]) -> List[Dict]:
        scenarios: List[Dict] = []
        has_quantiles = any(self._has_quantiles(store) for store in base_vrp_input.get("stores", []))
        if has_quantiles:
            scenarios.extend(self._quantile_scenarios(base_vrp_input))
        scenarios.extend(self._ratio_scenarios(base_vrp_input, demand_ratios))
        scenarios.extend(self._monte_carlo_scenarios(base_vrp_input))
        return scenarios
