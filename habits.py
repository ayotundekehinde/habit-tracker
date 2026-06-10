"""Habit tracking module."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Habit:
    name: str
    completed_dates: set[date] = field(default_factory=set)

    def mark_complete(self, day: date | None = None) -> None:
        self.completed_dates.add(day or date.today())

    def is_complete(self, day: date | None = None) -> bool:
        return (day or date.today()) in self.completed_dates

    def streak(self, as_of: date | None = None) -> int:
        current = as_of or date.today()
        count = 0
        while current in self.completed_dates:
            count += 1
            current = date.fromordinal(current.toordinal() - 1)
        return count


class HabitTracker:
    def __init__(self) -> None:
        self._habits: dict[str, Habit] = {}

    def add_habit(self, name: str) -> Habit:
        habit = Habit(name=name)
        self._habits[name] = habit
        return habit

    def get_habit(self, name: str) -> Habit | None:
        return self._habits.get(name)

    def list_habits(self) -> list[Habit]:
        return list(self._habits.values())
