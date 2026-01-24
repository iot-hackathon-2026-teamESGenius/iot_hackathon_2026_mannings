"""
Example usage of route optimization algorithms
"""

from models.customer import Customer
from models.vehicle import Vehicle
from algorithms.greedy.nearest_neighbor import NearestNeighbor
from algorithms.greedy.savings import SavingsAlgorithm
from utils.distance import create_distance_matrix, haversine_distance


def create_sample_problem():
    """
    Create a sample VRP problem for testing
    
    Returns:
        tuple: (customers, vehicles, depot, distance_matrix)
    """
    # Define depot
    depot = (40.7128, -74.0060)  # New York City coordinates
    
    # Define customers with demands
    customers = [
        Customer(1, 40.7580, -73.9855, 10),  # Times Square
        Customer(2, 40.7589, -73.9851, 15),  # Near Times Square
        Customer(3, 40.7614, -73.9776, 8),   # Central Park South
        Customer(4, 40.7489, -73.9680, 12),  # Grand Central
        Customer(5, 40.7424, -74.0060, 20),  # Chelsea
        Customer(6, 40.7282, -73.9942, 10),  # Greenwich Village
        Customer(7, 40.7080, -74.0133, 15),  # Financial District
        Customer(8, 40.7061, -74.0087, 18),  # Battery Park
    ]
    
    # Define vehicles with capacity
    vehicles = [
        Vehicle(1, 50),
        Vehicle(2, 50),
        Vehicle(3, 50),
    ]
    
    # Create locations list (depot + customers)
    locations = [depot] + [(c.lat, c.lon) for c in customers]
    
    # Create distance matrix
    distance_matrix = create_distance_matrix(locations, haversine_distance)
    
    return customers, vehicles, depot, distance_matrix


def run_example():
    """
    Run example optimization with different algorithms
    """
    print("=" * 60)
    print("Vehicle Routing Problem - Algorithm Comparison")
    print("=" * 60)
    
    # Create problem
    customers, vehicles, depot, distance_matrix = create_sample_problem()
    
    print(f"\nProblem Details:")
    print(f"  - Depot: {depot}")
    print(f"  - Customers: {len(customers)}")
    print(f"  - Vehicles: {len(vehicles)}")
    print(f"  - Total Demand: {sum(c.demand for c in customers)}")
    print(f"  - Total Capacity: {sum(v.capacity for v in vehicles)}")
    
    # Algorithm 1: Nearest Neighbor
    print("\n" + "-" * 60)
    print("Algorithm 1: Nearest Neighbor")
    print("-" * 60)
    
    nn_algo = NearestNeighbor(distance_matrix, customers, vehicles, depot)
    nn_solution = nn_algo.solve()
    
    print(f"\nResults:")
    print(f"  - Routes: {nn_solution.vehicles_used}")
    print(f"  - Total Distance: {nn_solution.total_distance:.2f} km")
    print(f"  - Computation Time: {nn_solution.computation_time:.4f} seconds")
    
    for i, route in enumerate(nn_solution.routes, 1):
        print(f"\n  Route {i} (Vehicle {route.vehicle_id}):")
        print(f"    - Customers: {route.customers}")
        print(f"    - Distance: {route.total_distance:.2f} km")
        print(f"    - Load: {route.total_load:.2f}/{vehicles[i-1].capacity}")
    
    # Algorithm 2: Savings Algorithm
    print("\n" + "-" * 60)
    print("Algorithm 2: Clarke-Wright Savings")
    print("-" * 60)
    
    savings_algo = SavingsAlgorithm(distance_matrix, customers, vehicles, depot)
    savings_solution = savings_algo.solve()
    
    print(f"\nResults:")
    print(f"  - Routes: {savings_solution.vehicles_used}")
    print(f"  - Total Distance: {savings_solution.total_distance:.2f} km")
    print(f"  - Computation Time: {savings_solution.computation_time:.4f} seconds")
    
    for i, route in enumerate(savings_solution.routes, 1):
        print(f"\n  Route {i} (Vehicle {route.vehicle_id}):")
        print(f"    - Customers: {route.customers}")
        print(f"    - Distance: {route.total_distance:.2f} km")
        print(f"    - Load: {route.total_load:.2f}")
    
    # Compare algorithms
    print("\n" + "=" * 60)
    print("Comparison")
    print("=" * 60)
    print(f"\nNearest Neighbor:")
    print(f"  - Distance: {nn_solution.total_distance:.2f} km")
    print(f"  - Vehicles: {nn_solution.vehicles_used}")
    print(f"  - Time: {nn_solution.computation_time:.4f}s")
    
    print(f"\nSavings Algorithm:")
    print(f"  - Distance: {savings_solution.total_distance:.2f} km")
    print(f"  - Vehicles: {savings_solution.vehicles_used}")
    print(f"  - Time: {savings_solution.computation_time:.4f}s")
    
    # Calculate improvement
    if nn_solution.total_distance > 0:
        improvement = ((nn_solution.total_distance - savings_solution.total_distance) / 
                      nn_solution.total_distance * 100)
        print(f"\nImprovement: {improvement:.2f}%")


if __name__ == "__main__":
    run_example()
