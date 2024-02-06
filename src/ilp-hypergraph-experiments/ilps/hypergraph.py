from model import connections, timetable_trips, stations, get_station
from model_objects import Hyperedge, Connection, TrainStation
from settings import max_train_len_global
from itertools import combinations, product
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


def filter_valid_positioning(hyperedge: Hyperedge) -> bool:
    for cons in hyperedge.origin_arces.values():
        if not _well_ordere(tuple(con.arrangement_origin[2] for con in cons)):
            return False
    for cons in hyperedge.destination_arces.values():
        if not _well_ordere(tuple(con.arrangement_destination[2] for con in cons)):
            return False
    return True


def filter_timetable_trips(hyperedge: Hyperedge) -> bool:
    """Ensures timetable trips only happen between two stations."""
    for trip in timetable_trips:
        if (
            trip.origin in hyperedge.origin_arces.keys()
            and trip.destination in hyperedge.destination_arces.keys()
        ):
            if len(hyperedge.origin_arces) > 1 or len(hyperedge.destination_arces) > 1:
                return False
    return True


def _well_ordere(positions: tuple[int]) -> bool:
    if len(positions) != len(set(positions)):
        return False
    if sorted(positions) != list(range(len(positions))):
        return False
    return True


def generate_hyperedges() -> set[Hyperedge]:
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
                    for arces in combinations(arces_between[orig][dest], r=i)
                )
            )
        print("Number of hyperedges: ", len(hyperedges))
        # for station in stations:
        #     print("Processing station ", station.name)
        #     in_cons_inside: list[Connection] = []
        #     in_cons_outside: list[Connection] = []
        #     out_cons_inside: list[Connection] = []
        #     out_cons_outside: list[Connection] = []
        #     for con in connections:
        #         if con.destination == station:
        #             if con.inside:
        #                 in_cons_inside.append(con)
        #             else:
        #                 in_cons_outside.append(con)
        #         elif con.origin == station:
        #             if con.inside:
        #                 out_cons_inside.append(con)
        #             else:
        #                 out_cons_outside.append(con)
        #
        #     for i in range(1, max_train_len_global + 1):
        #         print("Building combinations. Number of arces per hyperedge: ", i)
        #         hyperedges.extend(
        #             (Hyperedge(*arces) for arces in combinations(in_cons_inside, r=i))
        #         )
        #         hyperedges.extend(
        #             (Hyperedge(*arces) for arces in combinations(in_cons_outside, r=i))
        #         )
        #         hyperedges.extend(
        #             (Hyperedge(*arces) for arces in combinations(out_cons_inside, r=i))
        #         )
        #         hyperedges.extend(
        #             (Hyperedge(*arces) for arces in combinations(out_cons_outside, r=i))
        #         )
    return set(hyperedges)


def get_filtered_hyperedges() -> set[Hyperedge]:
    unfiltered_hyperedges = generate_hyperedges()
    _write(
        h
        for h in unfiltered_hyperedges
        if not h.inside and h.has_arc_from_to(get_station("C"), get_station("D"))
        # and h.has_arc_from_to(get_station("C"), get_station("A"))
    )
    hyperedges: list[Hyperedge] = list(
        filter(
            lambda h: filter_length_train(h)
            and filter_valid_positioning(h)
            and filter_timetable_trips(h),
            unfiltered_hyperedges,
        )
    )
    return hyperedges


def time_generate_hyperedges() -> float:
    tic = time.perf_counter()
    hyperedges = get_filtered_hyperedges()
    toc = time.perf_counter()
    for x in hyperedges[:10]:
        print(x)
    print(len(hyperedges))
    print(f"\nRuntime: {toc-tic}s")
    return toc - tic


def configure_model(m: gp.Model) -> dict[Hyperedge, gp.Var]:
    hyperedges: set[Hyperedge] = get_filtered_hyperedges()
    inside_hyperedes: set[Hyperedge] = set(h for h in hyperedges if h.inside)
    print("Number of inside hyperedges: ", len(inside_hyperedes))

    variable_map: dict[Hyperedge, gp.Var] = dict(
        (h, m.addVar(vtype="B", name=str(h))) for h in hyperedges
    )

    m.setObjective(
        gp.quicksum(h.weight * var for h, var in variable_map.items()),
        gp.GRB.MINIMIZE,
    )
    fullfill_timetable_trips(m, variable_map)
    flow_constraints(m, variable_map)
    single_inside_hyperedge(m, variable_map)

    return variable_map


def fullfill_timetable_trips(m: gp.Model, variable_map: dict[Hyperedge, gp.Var]):
    for trip in timetable_trips:
        possible_hyperedges: tuple[gp.Var] = tuple(
            var
            for h, var in variable_map.items()
            if not h.inside and h.has_arc_from_to(trip.origin, trip.destination)
        )
        print("Length of possible_hyperedges: ", len(possible_hyperedges))
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


def run_hyper_model():
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
