"""PawPal+ core classes: tasks, pets, owner and the daily scheduler (see diagrams/uml.mmd)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from enum import Enum


class Priority(Enum):
    """How important a task is. Higher value = more important."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


VALID_FREQUENCIES = ("daily", "weekly", "once")
REPEAT_EVERY = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


@dataclass
class Task:
    """One occurrence of a pet care task, e.g. a walk, feeding or medication.

    Completing a daily or weekly task creates a new Task for the next occurrence.
    A Task does not reference its Pet; Owner.get_all_tasks() pairs them instead.
    """

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"          # walk, feeding, meds, enrichment, grooming...
    frequency: str = "daily"           # daily, weekly, once
    preferred_time: str | None = None  # morning, afternoon, evening, or None
    fixed_time: time | None = None     # must happen at exactly this time, e.g. meds at 08:00
    due_date: date | None = None       # first day this occurrence is due; None = any day
    last_completed: date | None = None

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {VALID_FREQUENCIES}")

    def mark_complete(self, on: date) -> Task | None:
        """Record that this task was done on the given date.

        Returns a new Task for the next occurrence (tomorrow for daily, in 7 days
        for weekly), or None for a one-time task.
        """
        self.last_completed = on
        step = REPEAT_EVERY.get(self.frequency)
        if step is None:
            return None
        return replace(self, due_date=on + step, last_completed=None)

    def is_due(self, on: date) -> bool:
        """Return True if this occurrence is not done yet and is due on or before the given date."""
        if self.last_completed is not None:
            return False
        return self.due_date is None or self.due_date <= on


@dataclass
class Pet:
    """A pet and the care tasks it needs."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove the first task with the given title.

        Raises ValueError if this pet has no task with that title.
        """
        for i, task in enumerate(self.tasks):
            if task.title == title:
                del self.tasks[i]
                return
        raise ValueError(f"{self.name} has no task titled {title!r}")


@dataclass
class Owner:
    """The pet owner, their available time and preferences."""

    name: str
    available_minutes: int = 120
    day_start: time = time(8, 0)
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.available_minutes < 0:
            raise ValueError("available_minutes cannot be negative")

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner.

        Raises ValueError if the owner already has a pet with that name.
        """
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every (pet, task) pair across all of this owner's pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class ScheduledTask:
    """A task placed in the day: when it happens, for which pet, and why."""

    task: Task
    pet: Pet
    start_time: time
    reason: str = ""

    def end_time(self) -> time:
        """Return when this task finishes (start_time + duration).

        Note: time + timedelta isn't supported; use datetime.combine(...) + timedelta.
        """
        pass


@dataclass
class SkippedTask:
    """A task that was left out of the plan, and why."""

    task: Task
    pet: Pet
    reason: str = ""


@dataclass
class DailyPlan:
    """The scheduler's output for one day."""

    date: date
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[SkippedTask] = field(default_factory=list)

    def total_minutes(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        pass

    def explain(self) -> str:
        """Return a readable explanation of the plan and why tasks were chosen or skipped."""
        pass


def _to_minutes(t: time) -> int:
    """Minutes after midnight, e.g. 08:30 -> 510."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Inverse of _to_minutes, e.g. 510 -> 08:30."""
    return time(minutes // 60, minutes % 60)


MINUTES_PER_DAY = 24 * 60


@dataclass
class Scheduler:
    """Builds a DailyPlan from an owner's pets, tasks and available time."""

    owner: Owner

    def generate_plan(self, on: date) -> DailyPlan:
        """Choose and order the tasks due on the given date and return the plan.

        Fixed-time tasks are placed first; the rest fill the remaining time.
        """
        plan = DailyPlan(date=on)
        due = [(pet, task) for pet, task in self.owner.get_all_tasks() if task.is_due(on)]
        pet_of = {id(task): pet for pet, task in due}
        remaining = self.owner.available_minutes
        busy: list[tuple[int, int]] = []  # (start, end) in minutes after midnight

        # 1. Fixed-time tasks, most important first, while time allows.
        fixed = self.sort_by_priority([t for _, t in due if t.fixed_time is not None])
        for task in fixed:
            pet = pet_of[id(task)]
            if task.duration_minutes > remaining:
                plan.skipped.append(SkippedTask(task, pet, self._no_time_reason(task, remaining)))
                continue
            start = _to_minutes(task.fixed_time)
            busy.append((start, start + task.duration_minutes))
            remaining -= task.duration_minutes
            plan.scheduled.append(ScheduledTask(
                task, pet, task.fixed_time,
                f"Fixed time at {task.fixed_time:%H:%M}; {task.priority.name.lower()} priority.",
            ))

        # 2. Flexible tasks by priority, placed in the earliest free slot from day_start.
        flexible = self.sort_by_priority([t for _, t in due if t.fixed_time is None])
        fits = self.fit_to_time(flexible, remaining)
        for task in flexible:
            pet = pet_of[id(task)]
            if not any(task is f for f in fits):
                plan.skipped.append(SkippedTask(task, pet, self._no_time_reason(task, remaining)))
                continue
            start = self._find_slot(busy, task.duration_minutes)
            if start is None:
                plan.skipped.append(SkippedTask(task, pet, "No free slot left today."))
                continue
            busy.append((start, start + task.duration_minutes))
            remaining -= task.duration_minutes
            plan.scheduled.append(ScheduledTask(
                task, pet, _to_time(start),
                f"{task.priority.name.capitalize()} priority; fits in the available time "
                f"({remaining} min left after this).",
            ))

        plan.scheduled.sort(key=lambda st: st.start_time)
        return plan

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered from highest to lowest priority.

        Ties go to the shorter task, so more tasks fit in the day.
        """
        return sorted(tasks, key=lambda t: (-t.priority.value, t.duration_minutes))

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by fixed_time, earliest first.

        Tasks without a fixed time go last, in alphabetical order.
        """
        return sorted(tasks, key=lambda t: (t.fixed_time is None, t.fixed_time or time.max, t.title))

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
        on: date | None = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs across all pets that match every filter given.

        pet_name: only that pet's tasks. completed: True for tasks done on `on`
        (default today), False for tasks not done that day. None skips a filter.
        """
        on = on or date.today()
        return [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if (pet_name is None or pet.name == pet_name)
            and (completed is None or (task.last_completed == on) == completed)
        ]

    def fit_to_time(self, tasks: list[Task], minutes: int) -> list[Task]:
        """Return the tasks that fit within the given number of minutes.

        Greedy: goes through tasks in the given order and keeps each one that
        still fits, so pass them already sorted by priority.
        """
        chosen = []
        for task in tasks:
            if task.duration_minutes <= minutes:
                chosen.append(task)
                minutes -= task.duration_minutes
        return chosen

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warnings for overlapping tasks in the plan (e.g. two fixed-time tasks)."""
        items = sorted(
            ((_to_minutes(st.start_time), st) for st in plan.scheduled), key=lambda x: x[0]
        )
        warnings = []
        for i, (start_a, a) in enumerate(items):
            end_a = start_a + a.task.duration_minutes
            for start_b, b in items[i + 1:]:
                if start_b >= end_a:
                    break
                warnings.append(
                    f"Conflict: {a.task.title} ({a.pet.name}) at {a.start_time:%H:%M} "
                    f"overlaps {b.task.title} ({b.pet.name}) at {b.start_time:%H:%M}."
                )
        return warnings

    def complete_task(self, pet_name: str, title: str, on: date) -> Task | None:
        """Mark the given pet's task that is due on `on` as done (searches across all pets).

        For daily and weekly tasks, the next occurrence is added to the same pet
        and returned. Raises ValueError if the pet has no task with that title due
        that day, so completing the same task twice in one day is rejected.
        """
        for pet, task in self.owner.get_all_tasks():
            if pet.name == pet_name and task.title == title and task.is_due(on):
                next_task = task.mark_complete(on)
                if next_task is not None:
                    pet.add_task(next_task)
                return next_task
        raise ValueError(f"No task {title!r} due for {pet_name!r} on {on:%Y-%m-%d}")

    def _find_slot(self, busy: list[tuple[int, int]], duration: int) -> int | None:
        """Earliest start (minutes after midnight) from day_start that avoids busy blocks."""
        start = _to_minutes(self.owner.day_start)
        for b_start, b_end in sorted(busy):
            if start + duration <= b_start:
                break
            start = max(start, b_end)
        return start if start + duration <= MINUTES_PER_DAY else None

    @staticmethod
    def _no_time_reason(task: Task, remaining: int) -> str:
        return (f"Not enough available time: needs {task.duration_minutes} min, "
                f"only {remaining} min left.")
