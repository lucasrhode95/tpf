"""
Contains methods to deal with time series
"""
# system imports
from datetime import datetime, timedelta

# framework imports
from .math import positive_int


def datetime_list(start: datetime, duration: timedelta, dt: timedelta) -> list:
    output = [start]
    end = start + duration
    next_timestamp = start + dt

    while next_timestamp < end:
        output.append(next_timestamp)
        next_timestamp += dt
    return output


class Point():
    """
    Represents a point of a time series. Each point contains a timestamp and
    a value.
    """

    def __init__(self, timestamp: datetime, value: any):
        self.timestamp = timestamp
        self.value = value

    def is_before(self, timestamp: datetime, closed_interval=False) -> bool:
        if closed_interval:
            return self.timestamp <= timestamp
        else:
            return self.timestamp < timestamp

    def is_after(self, timestamp: datetime, closed_interval=False) -> bool:
        if closed_interval:
            return self.timestamp >= timestamp
        else:
            return self.timestamp > timestamp

    @staticmethod
    def sort_key(point: 'Point'):
        return point.timestamp

    def copy(self) -> 'Point':
        return Point(
            timestamp=self.timestamp,
            value=self.value
        )


class TimeSeries():
    """
    Class to represent and manipulate a time series. Each point of the time
    series is represented by an object containing a timestamp
    (datetime.datetime) and a value (any python type, but usually float).

    https://en.wikipedia.org/wiki/Time_series
    """

    def __init__(self, max_length: int = None):
        self.max_length = self._initialize_max_length(max_length)
        self._points = []

    def _initialize_max_length(self, max_length: any) -> int:
        if max_length is not None:
            return positive_int(max_length)

        return None

    def _remove_first_n(self, n: int = 1) -> list:
        # equivalent to multiple list.pop(0) calls
        self._points = self._points[n:]

    def len(self) -> int:
        return len(self._points)

    def get_first(self) -> Point:
        return self._points[0]

    def get_first_value(self) -> any:
        return self.get_first().value

    def get_first_timestamp(self) -> datetime:
        return self.get_first().timestamp

    def get_first_before(self, timestamp: datetime,
                         closed_interval=False) -> Point:
        last_point = self.get_last()
        if last_point.is_before(timestamp, closed_interval):
            return last_point

        this_point: Point
        previous_point: Point = None
        for this_point in self._points:
            if this_point.is_after(timestamp, not closed_interval):
                return previous_point
            else:
                previous_point = this_point

        return previous_point

    def get_first_after(self, timestamp: datetime,
                        closed_interval=False) -> Point:
        first_point = self.get_first()
        if first_point.is_after(timestamp, closed_interval):
            return first_point

        this_point: Point
        previous_point: Point = None
        for this_point in reversed(self._points):
            if this_point.is_before(timestamp, not closed_interval):
                return previous_point
            else:
                previous_point = this_point

        return previous_point

    def get_last(self) -> Point:
        """
        Returns the most recent point from the time series
        """
        return self._points[-1]

    def get_last_value(self) -> any:
        """
        Returns the most recent value
        """
        return self.get_last().value

    def get_last_timestamp(self) -> datetime:
        """
        Returns the most recent timestamp
        """
        return self.get_last().timestamp

    def insert(self, timestamp: datetime, value: any) -> None:
        """
        Adds a new point to the time series
        """
        self.insert_point(Point(timestamp, value))

    def insert_point(self, point: Point) -> None:
        if self.is_full():
            self._remove_first_n(self._calculate_overflow() + 1)

        self._points.append(point)
        self._sort()

    def is_full(self) -> bool:
        if self.max_length is None:
            return False
        else:
            return self.max_length <= self.len()

    def _calculate_overflow(self) -> int:
        """
        Calculates the quantity of points that exceed the maximum TimeSeries
        size.
        """
        if self.max_length is None:
            return 0
        else:
            return max(0, len(self._points) - self.max_length)

    def _sort(self) -> None:
        """
        Makes sure that self._points is ordered by timestamp.
        """
        self._points.sort(key=Point.sort_key)

    def pop(self, index: int = -1) -> Point:
        return self._points.pop(index)

    def pop_first(self) -> Point:
        return self._points.pop(0)

    def empty(self) -> bool:
        return len(self._points) == 0
