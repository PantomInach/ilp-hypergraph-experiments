from ..model import connections, timetable_trips, stations
from ..model_objects import Hyperedge, Connection, TrainStation
from ..settings import max_train_len_global
from itertools import product, combinations_with_replacement
import gurobipy as gp
import time

from typing import Iterable


def _write(hs: Iterable[Hyperedge]):
    with open("hyperedges.txt", "w") as f:
        f.write("\n".join(str(h) for h in sorted(hs, key=lambda h: len(h.arces))))


def filter_length_train(hyperedge: Hyperedge) -> bool:
    for station, arces in hyperedge.origin_arces.items():
        if station.max_train_len < len(arces) or max_train_len_global < len(arces):
            return False
    for station, arces in hyperedge.destination_arces.items():
        if station.max_train_len < len(arces) or max_train_len_global < len(arces):
            return False
    return True


def filter_invalid_positioning(hyperedge: Hyperedge) -> bool:
    """
    A hyperedge between to station should have a valid positioning of its trains.
    """
    if hyperedge.inside:
        return True
    for cons in hyperedge.origin_arces.values():
        if not _well_ordere(tuple(con.arrangement_origin[2] for con in cons)):
            return False
    for cons in hyperedge.destination_arces.values():
        if not _well_ordere(tuple(con.arrangement_destination[2] for con in cons)):
            return False
    return True


def filter_invalid_timetable_trip(hyperedge: Hyperedge) -> bool:
    """
    If a hyperedge describes the train movement in a timetable trip, the trains can't change
    there composition.
    """
    if hyperedge.inside:
        return True
    for trip in timetable_trips:
        if hyperedge.has_arc_from_to(trip.origin, trip.destination):
            for arc in hyperedge.arces:
                if arc.arrangement_origin != arc.arrangement_destination:
                    return False
    return True


def _well_ordere(positions: tuple[int]) -> bool:
    if len(positions) != len(set(positions)):
        return False
    if sorted(positions) != list(range(len(positions))):
        return False
    return True


def generate_hyperedges(verbose=False) -> set[Hyperedge]:
    hyperedges: list[Hyperedge] = []
    arces_between: dict[TrainStation, dict[TrainStation, Connection]] = {
        s: dict((s1, []) for s1 in stations) for s in stations
    }
    for con in connections:
        arces_between[con.origin][con.destination].append(con)
    for orig, dest in product(stations, repeat=2):
        for i in range(1, max_train_len_global + 1):
            hyperedges.extend(
                (
                    Hyperedge(*arces)
                    for arces in combinations_with_replacement(
                        arces_between[orig][dest], r=i
                    )
                )
            )
        if verbose:
            print("Number of hyperedges: ", len(hyperedges))
    return set(hyperedges)


def get_filtered_hyperedges(verbose=False) -> set[Hyperedge]:
    if verbose:
        print("Generating hyperedges...")
    hyperedges = generate_hyperedges(verbose=verbose)
    if verbose:
        print("Filtering hyperedges...", end=" ", flush=True)
    hyperedges: list[Hyperedge] = list(
        filter(
            lambda h: filter_length_train(h)
            and filter_invalid_positioning(h)
            and filter_invalid_timetable_trip(h),
            hyperedges,
        )
    )
    if verbose:
        print("done")
        print("Hyperedges remaining: ", len(hyperedges))
    return hyperedges


def time_generate_hyperedges() -> float:
    tic = time.perf_counter()
    hyperedges = get_filtered_hyperedges()
    toc = time.perf_counter()
    for x in hyperedges[:10]:
        print(x)
    print(len(hyperedges))
    print(f"\nRuntime: {toc - tic}s")
    return toc - tic


def configure_model(m: gp.Model, verbose=False) -> dict[Hyperedge, gp.Var]:
    hyperedges: set[Hyperedge] = get_filtered_hyperedges(verbose=verbose)
    if verbose:
        print("Configuring model")

        print("Generating variables...", end=" ", flush=True)
    variable_map: dict[Hyperedge, gp.Var] = dict(
        (h, m.addVar(vtype="B", name=str(h))) for h in hyperedges
    )
    if verbose:
        print("done")

        print("Configuring objective function", end="", flush=True)
    m.setObjective(
        gp.quicksum(h.weight * var for h, var in variable_map.items()),
        gp.GRB.MINIMIZE,
    )
    if verbose:
        print(", timetable fullfillment", end="", flush=True)
    fullfill_timetable_trips(m, variable_map)
    if verbose:
        print(", flow constraints", end="", flush=True)
    flow_constraints(m, variable_map)
    if verbose:
        print(", enforcing of single hyperedge in trainstations")
    single_inside_hyperedge(m, variable_map)

    return variable_map


def fullfill_timetable_trips(m: gp.Model, variable_map: dict[Hyperedge, gp.Var]):
    for trip in timetable_trips:
        possible_hyperedges: tuple[gp.Var] = tuple(
            var
            for h, var in variable_map.items()
            if not h.inside and h.has_arc_from_to(trip.origin, trip.destination)
        )
        m.addConstr(
            gp.quicksum(possible_hyperedges) == 1,
            name="Trips need to be implemented",
        )


def single_inside_hyperedge(m: gp.Model, variable_map: dict[Hyperedge, gp.Var]):
    for station in stations:
        hyperedge_inside: list[Hyperedge] = []
        for h, var in variable_map.items():
            if h.inside and h.comes_from_station(station):
                hyperedge_inside.append(var)
        m.addConstr(
            gp.quicksum(hyperedge_inside) <= 1,
            "Only one hyperedge inside a train station",
        )


def flow_constraints(m: gp.Model, variable_map: dict[Hyperedge, gp.Var]):
    for station in stations:
        for arrangement in station.allowed_arrangements:
            inside_into: list[Hyperedge] = []
            inside_out: list[Hyperedge] = []
            outside_into: list[Hyperedge] = []
            outside_out: list[Hyperedge] = []
            for h in variable_map.keys():
                if h.inside:
                    if h.contains_origin_node(station, arrangement):
                        inside_out.append(h)
                    if h.contains_destination_node(station, arrangement):
                        inside_into.append(h)
                else:
                    if h.contains_origin_node(station, arrangement):
                        outside_out.append(h)
                    if h.contains_destination_node(station, arrangement):
                        outside_into.append(h)

            m.addConstr(
                gp.quicksum(variable_map[h] for h in outside_into)
                == gp.quicksum(variable_map[h] for h in inside_out)
            )
            m.addConstr(
                gp.quicksum(variable_map[h] for h in inside_into)
                == gp.quicksum(variable_map[h] for h in outside_out)
            )


def run_hyper_model(verbose=False):
    with gp.Model() as m:
        variable_map: dict[Connection, gp.Var] = configure_model(m, verbose=verbose)

        tic = time.perf_counter()
        m.optimize()
        toc = time.perf_counter()

        if verbose:
            print(f"Optimal objective value: {m.objVal}")
            print("Choosen edges:")
            for var in sorted(
                filter(lambda v: v.X, variable_map.values()), key=lambda v: v.VarName
            ):
                print(var.VarName)
            print(f"\nRuntime: {toc - tic}s")
