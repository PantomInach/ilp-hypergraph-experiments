from enum import Enum
from typing import Final, FrozenSet, Iterable

# Describes a trains possible arrangements at a station
# Contains (train_type, train_orientation, train_position)
type TrainArrangment = tuple[int, bool, int]

train_types: Final[int] = 2
max_train_len_global: Final[int] = 3
train_arrangements: FrozenSet[TrainArrangment] = frozenset(
    (
        (t, o, p)
        for t in range(train_types)
        for o in (True, False)
        for p in range(max_train_len_global)
    )
)


class ConnectionType(Enum):
    ThroughTurn = 1
    DeadEndTurn = 2
    TurnaroundTrip = 3
    DeadheadTrip = 4


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
