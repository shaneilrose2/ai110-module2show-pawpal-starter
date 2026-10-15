"""PawPal+ core classes (skeletons generated from diagrams/uml.mmd).

Attributes and method signatures only -- scheduling logic is not implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum


class Priority(Enum):
    """How important a task is. Higher value = more important."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    """A single pet care task, e.g. a walk, feeding or medication."""

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"          # walk, feeding, meds, enrichment, grooming...
    frequency: str = "daily"           # daily, weekly, once
    preferred_time: str | None = None  # morning, afternoon, evening, or None
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        pass

    def is_due_today(self) -> bool:
        """Return True if this task should be scheduled today."""
        pass


@dataclass
class Pet:
    """A pet and the care tasks it needs."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        pass

    def remove_task(self, title: str) -> None:
        """Remove the task with the given title."""
        pass


@dataclass
class Owner:
    """The pet owner, their available time and preferences."""

    name: str
    available_minutes: int = 120
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        pass


@dataclass
class ScheduledTask:
    """A task placed in the day: when it happens, for which pet, and why."""

    task: Task
    pet: Pet
    start_time: time
    reason: str = ""

    def end_time(self) -> time:
        """Return when this task finishes (start_time + duration)."""
        pass


@dataclass
class DailyPlan:
    """The scheduler's output for one day."""

    date: date
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)

    def total_minutes(self) -> int:
        """Return the total minutes of all scheduled tasks."""
        pass

    def explain(self) -> str:
        """Return a readable explanation of the plan and why tasks were chosen or skipped."""
        pass


@dataclass
class Scheduler:
    """Builds a DailyPlan from an owner's pets, tasks and available time."""

    owner: Owner

    def generate_plan(self) -> DailyPlan:
        """Choose and order today's tasks and return the plan."""
        pass

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered from highest to lowest priority."""
        pass

    def fit_to_time(self, tasks: list[Task], minutes: int) -> list[Task]:
        """Return the tasks that fit within the given number of minutes."""
        pass

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warnings for overlapping or conflicting tasks in the plan."""
        pass
