"""
Standardized output format for optimization results.
符合GitHub Hackathon输出规范的优化结果格式
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class OptimizationResult:
    """
    Standard optimization result format required by GitHub Hackathon.
    
    符合GitHub Hackathon要求的标准输出格式。
    
    Fields:
        routes: List of routes, each containing vehicle path sequence
        total_distance: Total travel distance in km
        total_time: Total delivery time in minutes
        vehicles_used: Number of vehicles used
        sla_risk_score: SLA violation risk score (0-1, higher = more risk)
        scenario_id: Scenario identifier (for robust optimization)
    """
    
    routes: List[List[int]] = field(default_factory=list)
    """List of routes: each route is a list of store IDs (excluding depot 0)"""
    
    total_distance: float = 0.0
    """Total travel distance in kilometers"""
    
    total_time: float = 0.0
    """Total delivery time in minutes"""
    
    vehicles_used: int = 0
    """Number of vehicles used in the solution"""
    
    sla_risk_score: float = 0.0
    """SLA risk score: 0=no risk, 1=all stores unserved"""
    
    scenario_id: Optional[str] = None
    """Scenario identifier (e.g., 'ratio_0.9', 'quantile_low', 'mc_sample_1')"""
    
    # Optional extended fields
    computation_time: float = 0.0
    """Computation time in seconds"""
    
    optimization_type: str = "standard"
    """Optimization type: 'standard' or 'robust'"""
    
    scenario_comparison: Optional[Dict] = None
    """Scenario comparison results (for robust optimization)"""
    
    dropped_nodes: List[int] = field(default_factory=list)
    """List of unserved store IDs"""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format for JSON export."""
        return {
            'routes': self.routes,
            'total_distance': round(self.total_distance, 2),
            'total_time': round(self.total_time, 2),
            'vehicles_used': self.vehicles_used,
            'sla_risk_score': round(self.sla_risk_score, 4),
            'scenario_id': self.scenario_id,
            'computation_time': round(self.computation_time, 2),
            'optimization_type': self.optimization_type,
            'dropped_nodes': self.dropped_nodes,
        }
    
    @staticmethod
    def from_solution_dict(solution_dict: Dict) -> 'OptimizationResult':
        """
        Convert standard solution dictionary to OptimizationResult.
        
        Args:
            solution_dict: Solution from solver.solve_vrp()
        
        Returns:
            OptimizationResult instance
        """
        # Extract routes
        routes = []
        for route in solution_dict.get('routes', []):
            route_sequence = [node for node in route['sequence'] if node != 0]
            routes.append(route_sequence)
        
        # Calculate SLA risk score
        dropped_count = len(solution_dict.get('dropped_nodes', []))
        total_stores = sum(1 for _ in solution_dict.get('routes', []))
        sla_risk = dropped_count / max(total_stores, 1) if total_stores > 0 else 0
        
        return OptimizationResult(
            routes=routes,
            total_distance=solution_dict.get('total_distance', 0) / 100,  # Convert from 0.01 km units
            total_time=solution_dict.get('total_time', 0),
            vehicles_used=len(solution_dict.get('routes', [])),
            sla_risk_score=sla_risk,
            scenario_id=solution_dict.get('scenario_id'),
            computation_time=solution_dict.get('computation_time', 0),
            optimization_type=solution_dict.get('optimization_type', 'standard'),
            dropped_nodes=solution_dict.get('dropped_nodes', []),
        )


def convert_solution_to_github_format(solution_dict: Dict) -> Dict:
    """
    Convert internal solution format to GitHub Hackathon format.
    
    Args:
        solution_dict: Solution from solver.solve_vrp()
    
    Returns:
        Dictionary with OptimizationResult fields
    """
    result = OptimizationResult.from_solution_dict(solution_dict)
    return result.to_dict()
