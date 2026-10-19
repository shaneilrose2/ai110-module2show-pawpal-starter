from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

DAY = date(2026, 10, 18)


def test_mark_complete_changes_status():
    task = Task("Morning walk", 30)
    today = date(2026, 10, 18)
    assert task.last_completed is None
    assert task.is_due(today)

    task.mark_complete(today)

    assert task.last_completed == today
    assert not task.is_due(today)


def test_add_task_increases_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", 10))

    assert len(pet.tasks) == 1


# --- Task ---


def test_daily_task_is_due_again_next_day():
    task = Task("Walk", 30, frequency="daily")
    task.mark_complete(DAY)
    assert task.is_due(DAY + timedelta(days=1))


def test_weekly_task_waits_seven_days():
    task = Task("Bath", 20, frequency="weekly", last_completed=DAY)
    assert not task.is_due(DAY + timedelta(days=6))
    assert task.is_due(DAY + timedelta(days=7))


def test_once_task_never_due_after_completion():
    task = Task("Vet visit", 60, frequency="once")
    task.mark_complete(DAY)
    assert not task.is_due(DAY + timedelta(days=30))


def test_invalid_task_values_raise():
    with pytest.raises(ValueError):
        Task("Walk", 0)
    with pytest.raises(ValueError):
        Task("Walk", 30, frequency="monthly")


# --- Pet and Owner ---

def test_remove_task_by_title():
    pet = Pet("Mochi", "dog", tasks=[Task("Walk", 30), Task("Feed", 10)])
    pet.remove_task("Walk")
    assert [t.title for t in pet.tasks] == ["Feed"]


def test_remove_missing_task_raises():
    pet = Pet("Mochi", "dog")
    with pytest.raises(ValueError):
        pet.remove_task("Walk")


def test_duplicate_pet_name_raises():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog"))
    with pytest.raises(ValueError):
        owner.add_pet(Pet("Mochi", "cat"))


def test_get_all_tasks_includes_every_pet():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30)]))
    owner.add_pet(Pet("Biscuit", "cat", tasks=[Task("Feed", 10), Task("Play", 15)]))
    pairs = owner.get_all_tasks()
    assert [(p.name, t.title) for p, t in pairs] == [
        ("Mochi", "Walk"), ("Biscuit", "Feed"), ("Biscuit", "Play"),
    ]


# --- Scheduler ---

def test_sort_by_priority_high_first_then_shorter():
    tasks = [Task("Low", 5, Priority.LOW), Task("High long", 30, Priority.HIGH),
             Task("High short", 10, Priority.HIGH)]
    result = Scheduler(Owner("Jordan")).sort_by_priority(tasks)
    assert [t.title for t in result] == ["High short", "High long", "Low"]


def test_fit_to_time_skips_tasks_that_do_not_fit():
    tasks = [Task("A", 50), Task("B", 60), Task("C", 10)]
    result = Scheduler(Owner("Jordan")).fit_to_time(tasks, 60)
    assert [t.title for t in result] == ["A", "C"]


def test_plan_stays_within_available_time():
    owner = Owner("Jordan", available_minutes=40)
    owner.add_pet(Pet("Mochi", "dog", tasks=[
        Task("Walk", 30, Priority.HIGH), Task("Brush", 20, Priority.LOW),
    ]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert sum(s.task.duration_minutes for s in plan.scheduled) <= 40
    assert [s.task.title for s in plan.skipped] == ["Brush"]
    assert "Not enough available time" in plan.skipped[0].reason


def test_fixed_time_task_scheduled_at_its_time():
    owner = Owner("Jordan", day_start=time(7, 0))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Meds", 5, fixed_time=time(8, 0))]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled[0].start_time == time(8, 0)


def test_flexible_tasks_avoid_fixed_tasks():
    owner = Owner("Jordan", day_start=time(8, 0))
    owner.add_pet(Pet("Mochi", "dog", tasks=[
        Task("Meds", 10, fixed_time=time(8, 10)),
        Task("Walk", 30),
    ]))
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(DAY)
    walk = next(s for s in plan.scheduled if s.task.title == "Walk")
    assert walk.start_time == time(8, 20)
    assert scheduler.detect_conflicts(plan) == []


def test_plan_is_sorted_by_start_time():
    owner = Owner("Jordan", day_start=time(8, 0))
    owner.add_pet(Pet("Mochi", "dog", tasks=[
        Task("Dinner", 10, fixed_time=time(18, 0)), Task("Walk", 30),
    ]))
    plan = Scheduler(owner).generate_plan(DAY)
    times = [s.start_time for s in plan.scheduled]
    assert times == sorted(times)


def test_completed_task_left_out_of_plan():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, last_completed=DAY)]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled == [] and plan.skipped == []


def test_detect_conflicts_across_pets():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Meds", 10, fixed_time=time(8, 0))]))
    owner.add_pet(Pet("Biscuit", "cat", tasks=[Task("Feed", 10, fixed_time=time(8, 5))]))
    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts(scheduler.generate_plan(DAY))
    assert len(conflicts) == 1
    assert "Mochi" in conflicts[0] and "Biscuit" in conflicts[0]


def test_complete_task_only_affects_named_pet():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30)]))
    owner.add_pet(Pet("Biscuit", "cat", tasks=[Task("Walk", 10)]))
    scheduler = Scheduler(owner)
    scheduler.complete_task("Biscuit", "Walk", DAY)
    plan = scheduler.generate_plan(DAY)
    assert [s.pet.name for s in plan.scheduled] == ["Mochi"]


def test_empty_owner_gives_empty_plan():
    plan = Scheduler(Owner("Jordan")).generate_plan(DAY)
    assert plan.scheduled == [] and plan.skipped == []

def test_sort_by_time_earliest_first_flexible_last():
    tasks = [Task("Dinner", 10, fixed_time=time(18, 0)), Task("Play", 20),
             Task("Meds", 5, fixed_time=time(8, 0))]
    result = Scheduler(Owner("Jordan")).sort_by_time(tasks)
    assert [t.title for t in result] == ["Meds", "Dinner", "Play"]


def _two_pet_owner():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30, last_completed=DAY), Task("Brush", 15)]))
    owner.add_pet(Pet("Biscuit", "cat", tasks=[Task("Feed", 10)]))
    return Scheduler(owner)


def test_filter_by_pet_name():
    result = _two_pet_owner().filter_tasks(pet_name="Biscuit")
    assert [(p.name, t.title) for p, t in result] == [("Biscuit", "Feed")]


def test_filter_by_completion_status():
    scheduler = _two_pet_owner()
    assert [t.title for _, t in scheduler.filter_tasks(completed=True, on=DAY)] == ["Walk"]
    assert [t.title for _, t in scheduler.filter_tasks(completed=False, on=DAY)] == ["Brush", "Feed"]


def test_filter_by_pet_and_status():
    result = _two_pet_owner().filter_tasks(pet_name="Mochi", completed=False, on=DAY)
    assert [t.title for _, t in result] == ["Brush"]