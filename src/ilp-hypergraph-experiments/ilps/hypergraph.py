from model import connections, timetable_trips, stations
from model_objects import Hyperedge
from settings import max_train_len_global


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


def _well_ordere(positions: tuple[int]) -> bool:
    if len(positions) != len(set(positions)):
        return False
    if sorted(positions) != list(range(len(positions))):
        return False
    return True


def generate_hyperedges():
    raise NotImplementedError
