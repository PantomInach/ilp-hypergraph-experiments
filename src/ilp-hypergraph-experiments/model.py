from model_objects import TrainStation, Connection, TimeTableTrip

# Configure here the parameters of the model

# Stations: List of all trainstations
stations: tuple[TrainStation, ...] = tuple([
    TrainStation("A", 3),
    TrainStation("B", 3),
    TrainStation("C", 3),
    TrainStation("D", 2),
    TrainStation("E", 1),
])

def get_station(name: str) -> TrainStation | None:
    """
    Helperfunction to simply search for a train station by name.
    """
    for station in stations:
        if station.name == name:
            return station
    raise RuntimeError(f"Can't find station with name '{name}'.")

# Timetable trips: pairs of trainstations (origin, destination)
timetable_trips: tuple[TimeTableTrip] = tuple([
    TimeTableTrip(get_station("A"), get_station("B")),
    TimeTableTrip(get_station("B"), get_station("C")),
    TimeTableTrip(get_station("C"), get_station("D")),
    TimeTableTrip(get_station("D"), get_station("E")),
    TimeTableTrip(get_station("E"), get_station("A")),
    TimeTableTrip(get_station("C"), get_station("A")),
])

# Distance between stations as adjecency list.
# Pairs of TrainStation not in list are unreachable from each other.
#   |  A  B  C  D  E From
# --+---------------
# A |  N 10 20 25  N
# B |  N  N 10 15 30
# C | 25  N  N  5 10
# D | 20 30  N  N  5
# E | 10 15  N  N  N
# To
distance: dict[TrainStation, dict[TrainStation, int | None]] = {
        get_station("A"): {get_station("A"): None, get_station("B"): 10, get_station("C"): 20, get_station("D"): 25, get_station("E"): None},
        get_station("B"): {get_station("A"): None, get_station("B"): None, get_station("C"): 10, get_station("D"): 15, get_station("E"): 30},
        get_station("C"): {get_station("A"): 25, get_station("B"): None, get_station("C"): None, get_station("D"): 5, get_station("E"): 10},
        get_station("D"): {get_station("A"): 20, get_station("B"): 30, get_station("C"): None, get_station("D"): None, get_station("E"): 5},
        get_station("E"): {get_station("A"): 10, get_station("B"): 15, get_station("C"): None, get_station("D"): None, get_station("E"): None},
}

# Functions for easier working with the distances.
def get_distance(stationA: TrainStation, stationB: TrainStation) -> int | None:
    adj: dict[TrainStation, int] = distance.get(stationA)
    if adj:
        return adj.get(stationB)
    else:
        return None

def get_distance_trip(trip: TimeTableTrip) -> int | None:
    return get_distance(trip.origin, trip.destination)

# Describe here the connections between stations.
# Each timetable trip needs at least one connection between two stations.
connections: set[Connection] = set()
# Adds timetable trip turns
for trip in timetable_trips:
    dist = get_distance_trip(trip)
    if dist:
        connections.update(trip.get_all_connections(dist))

# Add all other connections between stations themself.
# Station A allow almost everything.
connections.update(get_station("A").get_connections(get_station("A"), weight=0)) # Station A direct turn
connections.update(get_station("A").get_connections_turnaround(get_station("A"), weight=1, preserve_position=False)) # Station A turnaround turn with coupling
connections.update(get_station("A").get_connections_deadhead_trip(get_station("A"), weight=10)) # Station A deadhead trips turn
# Allow split up at Station B
connections.update(get_station("B").get_connections(get_station("B"), weight=0, preserve_position=False))
# Allow split up at station C
connections.update(get_station("C").get_connections(get_station("C"), weight=0, preserve_position=False))
# Staion D only direct through turns.
connections.update(get_station("D").get_connections(get_station("D"), weight=0))
# Staion E only direct through turns.
connections.update(get_station("E").get_connections(get_station("E"), weight=0))
connections.update(get_station("E").get_connections_turnaround(get_station("E"), weight=0))

# The connections between all other staions are modelled by deadhead trips with extra distance 10, if the stations are connected.
for origin in stations:
    for dest in stations:
        if origin == dest:
            continue
        dist = get_distance(origin, dest)
        if dist is None:
            continue
        connections.update(origin.get_connections_deadhead_trip(dest, weight=dist + 10))

# Filter duplicated connections


if __name__ == "__main__":
    # Test if the given model is configured right.
    # Test if all TrainStation have different names
    names: list[str] = sorted(map(lambda s: s.name, stations))
    for i in range(len(names) - 1):
        if names[i] == names[i + 1]:
            raise RuntimeError(f"Got two trainstations with the same name '{names[i]}'.")

    # Test if all timetable trips are connected by a Connection
    for trip in timetable_trips:
        stationA: TrainStation = trip.origin
        stationB: TrainStation = trip.destination

        trip_serviced: bool = False
        for connection in connections:
            if connection.origin == stationA and connection.destination == stationB and connection.arrangement_origin in stationA.allowed_arrangements and connection.arrangement_destination in stationB.allowed_arrangements:
                trip_serviced = True
                break
        if not trip_serviced:
            raise RuntimeError(f"The timetable trip from '{stationA.name}' to '{stationB.name}' can't be serviced since they are not connection or no suitable train can be run between them two.")
    print("Configuration looks fine.")
    pass
