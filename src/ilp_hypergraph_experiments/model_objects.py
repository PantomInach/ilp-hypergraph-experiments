from typing import Final, FrozenSet, Iterable, Self

from ilp_hypergraph_experiments.settings import train_types, max_train_len_global

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
        possible_arrangements: Iterable[TrainArrangment] | None = None,
        disallow_arrangements: Iterable[TrainArrangment] | None = None,
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

    def __str__(self):
        return f"Station {self.name}"

    def discard_arrangements_by(
        self,
        types: Iterable[int] | None = None,
        orientations: Iterable[bool] | None = None,
        positions: Iterable[int] | None = None,
    ) -> Self:
        """
        Filters allowed arrangements by the given arguments and returns the trainstation.
        """
        if types:
            self.allowed_arrangements = set(
                arrangement
                for arrangement in self.allowed_arrangements
                if not arrangement[0] in types
            )
        if orientations:
            self.allowed_arrangements = set(
                arrangement
                for arrangement in self.allowed_arrangements
                if not arrangement[1] in orientations
            )
        if types:
            self.allowed_arrangements = set(
                arrangement
                for arrangement in self.allowed_arrangements
                if not arrangement[2] in positions
            )
        return self

    def get_connections(
        self,
        destination: "TrainStation",
        weight: int,
        preserve_position: bool = True,
        inside: bool = False,
    ) -> list["Connection"]:
        """
        Returns all direct turns between the stations as connections.

        -@ preserve_position: Disallows coupling or uncoupling in most cases.
        """
        if preserve_position:
            possible_direct = self.allowed_arrangements.intersection(
                destination.allowed_arrangements
            )
            return list(
                Connection(
                    self, destination, weight, arrangement, arrangement, inside=inside
                )
                for arrangement in possible_direct
            )
        else:
            return list(
                Connection(
                    self, destination, weight, arr_origin, arr_dest, inside=inside
                )
                for arr_origin in self.allowed_arrangements
                for arr_dest in destination.allowed_arrangements
                if arr_origin[0] == arr_dest[0] and arr_origin[1] == arr_dest[1]
            )

    def get_connections_turnaround(
        self,
        destination: "TrainStation",
        weight: int,
        preserve_position: bool = True,
        inside: bool = False,
    ) -> list["Connection"]:
        """
        Returns all turnaround turns between the stations as connections.

        -@ preserve_position: Disallows coupling or uncoupling in most cases.
        """
        return list(
            Connection(self, destination, weight, arr_origin, arr_dest, inside=inside)
            for arr_origin in self.allowed_arrangements
            for arr_dest in destination.allowed_arrangements
            if arr_origin[0] == arr_dest[0]
            and arr_origin[1] != arr_dest[1]
            and (arr_origin[2] == arr_dest[2] or not preserve_position)
        )

    def get_connections_deadhead_trip(
        self, destination: "TrainStation", weight: int, inside: bool = False
    ) -> list["Connection"]:
        """
        Returns all trips between the stations as connections.
        This maps all arranements to all arrangements if the type of the trains is preserved.
        Here deadhead and normal trips are differentiated, but can be described by the weight of the connection.

        This function calculates the same as get_connections_turnaround, but is kept for real world modelling analogies.
        """
        return self.get_connections_turnaround(
            destination, weight, preserve_position=False, inside=inside
        )


class Connection(object):
    """
    Describes a connection between two stations outside of a timetable trip.
    """

    def __init__(
        self,
        origin: TrainStation,
        destination: TrainStation,
        weight: int,
        arrangement_origin: TrainArrangment,
        arrangement_destination: TrainArrangment,
        inside: bool = False,
    ):
        self.origin: TrainStation = origin
        self.destination: TrainStation = destination
        self.weight: int = weight
        self.arrangement_origin: TrainArrangment = arrangement_origin
        self.arrangement_destination: TrainArrangment = arrangement_destination
        self.inside: bool = inside
        if self.origin != self.destination and self.inside:
            raise RuntimeError(
                f"The connection between station {self.origin} and {self.destination} can't be a connection inside a trainstation."
            )

    def __str__(self):
        return f"{self.origin.name} -> {self.destination.name} with {self.arrangement_origin} --{self.weight}--> {self.arrangement_destination}"


class TimeTableTrip(object):
    """
    Implements a timetble trip.
    In this implementation timetable trips are timeless.
    """

    def __init__(self, stationA: TrainStation, stationB: TrainStation):
        self.origin: TrainStation = stationA
        self.destination: TrainStation = stationB

    def get_all_connections(self, weight: int) -> list[Connection, ...]:
        return self.origin.get_connections(self.destination, weight)

    def __str__(self):
        return "From " + self.origin.name + " to " + self.destination.name


class Hyperedge(object):
    """
    Hyperedge between trainstations.
    """

    def __init__(self, *connections: Connection, inside: bool = False):
        self.arces: set[Connection] = set(con for con in connections if con is not None)
        self.weight: int = sum((arc.weight for arc in self.arces))
        self.inside: bool = inside
        if all(con.inside for con in self.arces):
            self.inside: bool = True
        self.origins: set[tuple[TrainStation, TrainArrangment]] = set(
            ((arc.origin, arc.arrangement_origin) for arc in self.arces)
        )
        self.destinations: set[tuple[TrainStation, TrainArrangment]] = set(
            ((arc.destination, arc.arrangement_destination) for arc in self.arces)
        )
        self.origin_arces: dict[TrainStation, list[Connection]] = {}
        self.destination_arces: dict[TrainStation, list[Connection]] = {}
        for arc in self.arces:
            self.origin_arces.setdefault(arc.origin, [])
            self.origin_arces[arc.origin].append(arc)
            self.destination_arces.setdefault(arc.destination, [])
            self.destination_arces[arc.destination].append(arc)
        num_origins: int = len(set(s for (s, _) in self.origins))
        num_destinations: int = len(set(s for (s, _) in self.destinations))
        if num_origins > 1 and num_destinations > 1:
            raise RuntimeError(
                "Hypheredges can not map from multiple stations to multiple stations."
            )

    def __str__(self):
        res = f"Hyperedge of weight {self.weight}:"
        for arc in self.arces:
            res += "\n " + str(arc)
        return res

    def has_arc_from_to(self, origin: TrainStation, destination: TrainStation) -> bool:
        for arc in self.arces:
            if arc.origin == origin and arc.destination == destination:
                return True
        return False

    def has_arc_from_to_arr(
        self,
        origin: TrainStation,
        origin_arrangement: TrainArrangment,
        destination: TrainStation,
        destination_arrangement: TrainArrangment,
    ) -> bool:
        for arc in self.arces:
            if (
                arc.origin == origin
                and arc.arrangement_origin == origin_arrangement
                and arc.destination == destination
                and arc.arrangement_destination == destination_arrangement
            ):
                return True
        return False

    def contains_destination_node(
        self, station: TrainStation, arrangement: TrainArrangment
    ) -> bool:
        for arc in self.arces:
            if (
                arc.destination == station
                and arc.arrangement_destination == arrangement
            ):
                return True
        return False

    def contains_origin_node(
        self, station: TrainStation, arrangement: TrainArrangment
    ) -> bool:
        for arc in self.arces:
            if arc.origin == station and arc.arrangement_origin == arrangement:
                return True
        return False

    def runs_to_station(self, station: TrainStation) -> bool:
        for arc in self.arces:
            if arc.destination == station:
                return True
        return False

    def comes_from_station(self, station: TrainStation) -> bool:
        for arc in self.arces:
            if arc.origin == station:
                return True
        return False


if __name__ == "__main__":
    s1 = TrainStation("A")
    s2 = TrainStation("B")
    con = Connection(s1, s2, 10, (1, True, 1), (1, False, 1))
    print(con)
