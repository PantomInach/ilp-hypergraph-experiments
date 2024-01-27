from typing import Final, FrozenSet, Iterable, Self

from settings import train_types, max_train_len_global

# Describes a trains possible arrangements at a station
# Contains (train_type, train_orientation, train_position)
type TrainArrangment = tuple[int, bool, int]

train_arrangements: FrozenSet[TrainArrangment] = frozenset(
    (
        (t, o, p)
        for t in range(train_types)
        for o in (True, False)
        for p in range(max_train_len_global)
    )
)

class TrainStation(object):
    def __init__(
        self,
        name: str,
        max_train_len_station: int = 1,
        possible_arrangements: Iterable[TrainArrangment] = None,
        disallow_arrangements: Iterable[TrainArrangment] = None,
    ):
        self.name: str = name
        if max_train_len_station > max_train_len_global:
            raise RuntimeError(
                f"The maximum length the station '{max_train_len_station}' can supports exceeds the maximum allowed train lenght of {max_train_len_global}."
            )
        self.max_train_len: Final[int] = max_train_len_station

        self.allowed_arrangements: set[TrainArrangment] = set(train_arrangements)
        if possible_arrangements:
            self.allowed_arrangements: set[TrainArrangment] = set(possible_arrangements)
        elif disallow_arrangements:
            self.allowed_arrangements -= set(disallow_arrangements)

    def discard_arrangements_by(self, types: Iterable[int] | None = None, orientations: Iterable[bool] | None = None, positions: Iterable[int] | None = None) -> Self:
        """
        Filters allowed arrangements by the given arguments and returns the trainstation.
        """
        if types:
            self.allowed_arrangements = set(arrangement for arrangement in self.allowed_arrangements if not arrangement[0] in types)
        if orientations:
            self.allowed_arrangements = set(arrangement for arrangement in self.allowed_arrangements if not arrangement[1] in orientations)
        if types:
            self.allowed_arrangements = set(arrangement for arrangement in self.allowed_arrangements if not arrangement[2] in positions)
        return self

    def get_connections(self):
        # TODO: how to model turns and trips between stations
        pass

class Connection(object):
    """
    Describes a connection between two stations outside of a timetable trip.
    """
    def __init__(self, origin: TrainStation, destination: TrainStation, weight: int, arrangement_origin: TrainArrangment, arrangement_destination):
        self.origin: TrainStation = origin
        self.destination: TrainStation = destination
        self.weight: int = weight
        self.arrangement_origin: TrainArrangment = arrangement_origin
        self.arrangement_destination: TrainArrangment = arrangement_destination

class TimeTableTrip(object):
    """
    Implements a timetble trip.
    In this implementation timetable trips are timeless.
    """

    def __init__(self, stationA: TrainStation, stationB: TrainStation):
        self.origin: TrainStation = stationA
        self.destination: TrainStation = stationB

        self._allowed_in_and_out_arrangements: None | set[TrainArrangment] = None

    def get_allowed_in_and_out_arrangements(self) -> set[TrainArrangment]:
        if not self._allowed_in_and_out_arrangements:
            self._allowed_in_and_out_arrangements = (
                self.origin.allowed_arrangements.intersection(
                    self.destination.allowed_arrangements
                )
            )
        return self._allowed_in_and_out_arrangements

    def get_all_connections(self, weight: int) -> list[Connection,...]:
        return list(Connection(self.origin, self.destination, weight, arrangement, arrangement) for arrangement in self.get_allowed_in_and_out_arrangements())
