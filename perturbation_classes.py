import gurobipy as gp
from gurobipy import GRB

class PathAttack:
    name = "PathAttack"
    def __init__(self, config, write_model=False, verbose=False):
        self.write_model = write_model
        self.verbose = verbose
        self.c = config

        self.paths = set()
        self.all_path_edges = set()
        self.d = dict()
        self.path_constraints = dict()
        self.edge_upper_bounds = dict()

        env = gp.Env(empty=True)
        if not self.verbose: env.setParam('OutputFlag', 0)
        env.start()
        self.model = gp.Model("Spanner Attack", env=env)

    def add_paths(self, paths):
        for path in paths:
            self.paths.add(path)
            path_edges = list(zip(path[:-1], path[1:]))
            new_edges = set(path_edges).difference(self.all_path_edges)
            self.all_path_edges.update(new_edges)
            for edge in new_edges:
                self.d[edge] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0)
                self.edge_upper_bounds[edge] = self.model.addConstr(self.d[edge] <= self.c.local_budget)
            self.path_constraints[path] = self.model.addConstr(gp.quicksum((self.c.G.edges[a, b]["weight"]+self.d[(a,b)]) for a,b in zip(path[:-1], path[1:])) >= self.c.goal)
        total_perturbations = gp.quicksum(self.d.values())
        self.global_budget_constraint = self.model.addConstr(total_perturbations <= self.c.global_budget, name="global_budget") 
        self.model.setObjective(total_perturbations, sense=GRB.MINIMIZE) 

    def perturb(self):
        result_dict = {}

        if self.write_model: self.model.write("final model.lp")

        self.model.optimize()

        result_dict["LP Status"] = self.model.status

        if self.model.status == GRB.OPTIMAL:
            result_dict["Perturbation Dict"] = { k : v.X for k,v in self.d.items() if v.X != 0}
            result_dict["Total Perturbations"] = self.model.objVal
            result_dict["Global Budget Slack"] = self.global_budget_constraint.Slack
            result_dict["Supporting Paths"] = [path for path in self.paths if self.path_constraints[path].Slack == 0]
        elif self.model.status == GRB.INFEASIBLE:
            self.model.computeIIS()
            result_dict["IIS_paths"] = [path for path in self.paths if self.path_constraints[path].IISConstr]
            result_dict["IIS_edges"] = [edge for edge in self.all_path_edges if self.edge_upper_bounds[edge].IISConstr]
            result_dict["IIS_global_budget"] = self.global_budget_constraint.IISConstr
        return result_dict