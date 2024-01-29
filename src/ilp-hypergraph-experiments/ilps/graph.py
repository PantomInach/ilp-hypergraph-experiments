# from model import connections, stations, timetable_trips

# Solve the following MIP:
#  maximize
#        x +   y + 2 z
#  subject to
#        x + 2 y + 3 z <= 4
#        x +   y       >= 1
#        x, y, z binary

from model import connections, stations, timetable_trips
from model_objects import Connection
import gurobipy as gp
import time


def configure_model(m: gp.Model) -> dict[Connection, gp.Var]:
    variable_map: dict[Connection, gp.Var] = dict((connection, m.addVar(vtype='B', name=str(connection))) for connection in connections)

    # Set objective function
    m.setObjective(gp.quicksum(con.weight * var for con, var in variable_map.items()), gp.GRB.MINIMIZE)

    # Add constraints
    # Fullfill timetable trips
    for trip in timetable_trips:
        trip_connections = tuple(var for con, var in variable_map.items() if con.origin == trip.origin and con.destination == trip.destination)
        m.addConstr(gp.quicksum(trip_connections) >= 1, name="Trips need to be implemented")
    # Flow constraints
    for station in stations:
        for arrangement in station.allowed_arrangements:
            out_edges = (variable_map[con] for con in connections if con.origin == station and arrangement == con.arrangement_origin)
            in_edges = (variable_map[con] for con in connections if con.destination == station and arrangement == con.arrangement_destination)
            m.addConstr(gp.quicksum(out_edges) == gp.quicksum(in_edges), name="Flow constraint")

    return variable_map

def run_model():
    with gp.Model() as m:
        configure_model(m)

        tic=time.perf_counter()
        m.optimize()
        toc=time.perf_counter()

        print(f"Optimal objective value: {m.objVal}")
        print(f"\nRuntime: {toc-tic}s")

if __name__ == '__main__':
    run_model()
