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
    variable_map: dict[Connection, gp.Var] = dict(
        (connection, m.addVar(vtype="B", name=str(connection)))
        for connection in connections
    )

    # Set objective function
    m.setObjective(
        gp.quicksum(con.weight * var for con, var in variable_map.items()),
        gp.GRB.MINIMIZE,
    )

    # Add constraints
    # Fullfill timetable trips
    for trip in timetable_trips:
        trip_connections = tuple(
            var
            for con, var in variable_map.items()
            if con.origin == trip.origin and con.destination == trip.destination
        )
        m.addConstr(
            gp.quicksum(trip_connections) >= 1, name="Trips need to be implemented"
        )
    # Flow constraints trainstations
    # Since the arrangements of each station represent the trains coming into and out of the trainstation,
    # we need to differ between edges which only flow inside the station and flow outside the station.
    for station in stations:
        for arrangement in station.allowed_arrangements:
            in_edges_outside: list[Connection, ...] = []
            in_edges_inside: list[Connection, ...] = []
            out_edges_outside: list[Connection, ...] = []
            out_edges_inside: list[Connection, ...] = []
            for con in connections:
                if con.inside:
                    if (
                        con.destination == station
                        and arrangement == con.arrangement_destination
                    ):
                        in_edges_inside.append(variable_map[con])
                    if con.origin == station and arrangement == con.arrangement_origin:
                        out_edges_inside.append(variable_map[con])
                else:
                    if (
                        con.destination == station
                        and arrangement == con.arrangement_destination
                    ):
                        in_edges_outside.append(variable_map[con])
                    if con.origin == station and arrangement == con.arrangement_origin:
                        out_edges_outside.append(variable_map[con])
            m.addConstr(
                gp.quicksum(in_edges_outside) == gp.quicksum(out_edges_inside),
                name="Flow constraint into stations",
            )
            m.addConstr(
                gp.quicksum(in_edges_inside) == gp.quicksum(out_edges_outside),
                name="Flow constraint out of stations",
            )
            # The constraint inside_in == inside_out is not needed since it is covered by the other two.
    # Flow constraint inside trainstations
    # Only choose as much trains as trainstations allows

    return variable_map


def run_model():
    with gp.Model() as m:
        variable_map: dict[Connection, gp.Var] = configure_model(m)

        tic = time.perf_counter()
        m.optimize()
        toc = time.perf_counter()

        print(f"Optimal objective value: {m.objVal}")
        print("Choosen edges:")
        for var in sorted(
            filter(lambda v: v.X, variable_map.values()), key=lambda v: v.VarName
        ):
            print(var.VarName)
        print(f"\nRuntime: {toc-tic}s")


if __name__ == "__main__":
    run_model()
