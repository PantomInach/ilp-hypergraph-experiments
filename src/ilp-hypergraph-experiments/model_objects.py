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

    def get_connections(self, destination: "TrainStation", weight:int, preserve_position: bool = True) -> list["Connection"]:
        """
        Returns all direct turns between the stations as connections.

        -@ preserve_position: Disallows coupling or uncoupling in most cases.
        """
        if preserve_position:
            possible_direct = self.allowed_arrangements.intersection(destination.allowed_arrangements)
            return list(Connection(self, destination, weight, arrangement, arrangement) for arrangement in possible_direct)
        else:
            return list(
                Connection(self, destination, weight, arr_origin, arr_dest)
                for arr_origin in self.allowed_arrangements
                for arr_dest in destination.allowed_arrangements
                if arr_origin[0] == arr_dest[0] and arr_origin[1] == arr_dest[1]
            )

    def get_connections_turnaround(self, destination: "TrainStation", weight: int, preserve_position: bool = True) -> list["Connection"]:
        """
        Returns all turnaround turns between the stations as connections.

        -@ preserve_position: Disallows coupling or uncoupling in most cases.
        """
        return list(
            Connection(self, destination, weight, arr_origin, arr_dest)
            for arr_origin in self.allowed_arrangements
            for arr_dest in destination.allowed_arrangements
            if arr_origin[0] == arr_dest[0] and arr_origin[1] != arr_dest[1] and (arr_origin[2] == arr_dest[2] or not preserve_position)
        )

    def get_connections_deadhead_trip(self, destination: "TrainStation", weight: int) -> list["Connection"]:
        """
        Returns all trips between the stations as connections.
        This maps all arranements to all arrangements if the type of the trains is preserved.
        Here deadhead and normal trips are differentiated, but can be described by the weight of the connection.

        This function calculates the same as get_connections_turnaround, but is kept for real world modelling analogies.
        """
        return self.get_connections_turnaround(destination, weight, preserve_position=False)

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

    def get_all_connections(self, weight: int) -> list[Connection,...]:
        return self.origin.get_connections(self.destination, weight)
