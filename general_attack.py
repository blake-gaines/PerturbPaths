from tqdm import tqdm
import time
import networkx as nx
import sys

class State:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# Make every path between s and t have length of at least goal
def attack(c):
    # path_selector = random_shortest_paths(G, path_selector.source, path_selector.target, goal, weight="weight")

    add_times = []
    perturb_times = []

    G = c.G.copy()
    if type(G) == nx.Graph:
        G = G.to_directed(as_view=True)

    state = State(
        G_prime=G.copy(),
        perturbation_dict=dict(),
        paths = set(),
        all_path_edges = set(),
        current_distance = c.path_selector.distance(G),
    )

    status= "Fail: Unknown"
    pbar = tqdm(range(c.max_iterations), desc=c.path_selector.name, position=1, leave=False)
    for i in pbar:
            # print("\nAdding\n")
            add_start_time = time.time()
            new_paths = c.path_selector.get_next(state=state)
            if not new_paths:
                status = "Fail: No Paths Returned"
                break
            else:
                state.paths.update(new_paths)
                for new_path in new_paths: 
                    state.all_path_edges.update(zip(new_path[:-1], new_path[1:]))
            add_times.append(time.time() - add_start_time)

            perturb_start_time = time.time()
            state.perturbation_dict = c.perturbation_function(G, state.paths, state.all_path_edges, c.goal, c.global_budget, c.local_budget)
            perturb_times.append(time.time() - perturb_start_time)

            if not state.perturbation_dict:
                status = "Fail: No Perturbations Returned"
                break

            G_prime = G.copy()
            for edge, perturbation in state.perturbation_dict.items():
                G_prime.edges[edge[0], edge[1]]["weight"] += perturbation

            state.current_distance = c.path_selector.distance(G_prime)
            pbar.set_description(f"Current Distance: {state.current_distance} | Goal: {c.goal}")
            
            if state.current_distance >= c.goal:
                break

            if c.path_selector.update_every_iteration:
                c.path_selector.update_graph(G_prime)

    if state.current_distance >= c.goal:
        status = "Success"
    elif c.max_iterations == i+1:
        status = "Fail: Max Iterations"

    stats_dict = {
        "Number of Paths": len(state.paths),
        "Number of Edges": len(state.all_path_edges),
        "Add Times": add_times,
        "Perturb Times": perturb_times,
        "Iterations": i+1,
        "Final Distance": state.current_distance,
        "Status": status
    }

    return state.perturbation_dict, stats_dict