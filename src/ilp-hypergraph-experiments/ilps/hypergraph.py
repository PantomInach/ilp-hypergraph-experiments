from model import connections, timetable_trips, stations
from model_objects import Hyperedge, Connection
from settings import max_train_len_global
from itertools import combinations
import time


def filter_length_train(hyperedge: Hyperedge) -> bool:
    for station, arces in hyperedge.origin_arces.items():
        if station.max_train_len > len(arces) or len(arces) > max_train_len_global:
            return False
    for station, arces in hyperedge.destination_arces.items():
        if station.max_train_len > len(arces) or len(arces) > max_train_len_global:
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
    for station in stations:
        print("Processing station ", station.name)
        in_cons_inside: list[Connection] = []
        in_cons_outside: list[Connection] = []
        out_cons_outside: list[Connection] = []
        for con in connections:
            if con.destination == station:
                if con.inside:
                    in_cons_inside.append(con)
                else:
                    in_cons_outside.append(con)
            elif con.origin == station and not con.inside:
                out_cons_outside.append(con)

        for i in range(1, max_train_len_global + 1):
            print("Building combinations. Number of arces per hyperedge: ", i)
            hyperedges.extend(
                (Hyperedge(*arces) for arces in combinations(in_cons_inside, r=i))
            )
            hyperedges.extend(
                (Hyperedge(*arces) for arces in combinations(in_cons_outside, r=i))
            )
            hyperedges.extend(
                (Hyperedge(*arces) for arces in combinations(out_cons_outside, r=i))
            )
            print("Number of hyperedges: ", len(hyperedges))
    return set(hyperedges)


def get_filtered_hyperedges() -> set[Hyperedge]:
    return list(
        filter(
            lambda h: filter_length_train(h)
            and filter_valid_positioning(h)
            and filter_timetable_trips(h),
            generate_hyperedges(),
        )
    )


def time_generate_hyperedges() -> float:
    tic = time.perf_counter()
    hyperedges = get_filtered_hyperedges()
    toc = time.perf_counter()
    for x in hyperedges[:10]:
        print(x)
    print(len(hyperedges))
    print(f"\nRuntime: {toc-tic}s")
    return toc - tic
