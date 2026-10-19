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


def test_completing_daily_task_creates_next_day_task():
    task = Task("Walk", 30, frequency="daily")
    next_task = task.mark_complete(DAY)
    assert next_task is not None and next_task is not task
    assert next_task.due_date == DAY + timedelta(days=1)
    assert next_task.last_completed is None
    assert not next_task.is_due(DAY)
    assert next_task.is_due(DAY + timedelta(days=1))
    assert not task.is_due(DAY + timedelta(days=1))  # the finished one stays done


def test_completing_weekly_task_creates_task_in_seven_days():
    next_task = Task("Bath", 20, frequency="weekly").mark_complete(DAY)
    assert next_task.due_date == DAY + timedelta(days=7)
    assert not next_task.is_due(DAY + timedelta(days=6))
    assert next_task.is_due(DAY + timedelta(days=7))


def test_next_occurrence_keeps_task_details():
    task = Task("Meds", 5, Priority.HIGH, category="meds", fixed_time=time(8, 0))
    next_task = task.mark_complete(DAY)
    assert (next_task.title, next_task.priority, next_task.fixed_time) == ("Meds", Priority.HIGH, time(8, 0))


def test_once_task_never_due_after_completion():
    task = Task("Vet visit", 60, frequency="once")
    assert task.mark_complete(DAY) is None
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


# --- Sorting and filtering ---

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


def test_complete_task_adds_next_occurrence_to_pet():
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", tasks=[Task("Walk", 30)])
    owner.add_pet(mochi)
    scheduler = Scheduler(owner)

    next_task = scheduler.complete_task("Mochi", "Walk", DAY)

    assert len(mochi.tasks) == 2 and mochi.tasks[-1] is next_task
    assert [s.task.title for s in scheduler.generate_plan(DAY).scheduled] == []
    tomorrow = scheduler.generate_plan(DAY + timedelta(days=1))
    assert [s.task for s in tomorrow.scheduled] == [next_task]


def test_complete_task_twice_completes_next_occurrence():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30)]))
    scheduler = Scheduler(owner)
    scheduler.complete_task("Mochi", "Walk", DAY)
    third = scheduler.complete_task("Mochi", "Walk", DAY + timedelta(days=1))
    assert third.due_date == DAY + timedelta(days=2)
    assert len(owner.pets[0].tasks) == 3


# --- Edge cases ---

def test_pet_with_no_tasks_gives_empty_plan():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog"))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled == [] and plan.skipped == []


def test_two_tasks_at_exact_same_time_conflict():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[
        Task("Meds", 10, fixed_time=time(8, 0)), Task("Feed", 10, fixed_time=time(8, 0)),
    ]))
    scheduler = Scheduler(owner)
    assert len(scheduler.detect_conflicts(scheduler.generate_plan(DAY))) == 1


def test_back_to_back_tasks_do_not_conflict():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[
        Task("Meds", 10, fixed_time=time(8, 0)), Task("Feed", 10, fixed_time=time(8, 10)),
    ]))
    scheduler = Scheduler(owner)
    assert scheduler.detect_conflicts(scheduler.generate_plan(DAY)) == []


def test_sort_by_time_ties_broken_by_title():
    tasks = [Task("Zoomies", 5, fixed_time=time(8, 0)), Task("Apple treat", 5, fixed_time=time(8, 0))]
    result = Scheduler(Owner("Jordan")).sort_by_time(tasks)
    assert [t.title for t in result] == ["Apple treat", "Zoomies"]


def test_task_exactly_filling_available_time_is_scheduled():
    owner = Owner("Jordan", available_minutes=30)
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30)]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert len(plan.scheduled) == 1 and plan.skipped == []


def test_zero_available_minutes_skips_everything():
    owner = Owner("Jordan", available_minutes=0)
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30), Task("Feed", 5)]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled == [] and len(plan.skipped) == 2


def test_fixed_task_before_day_start_keeps_its_time():
    owner = Owner("Jordan", day_start=time(9, 0))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Meds", 5, fixed_time=time(7, 0))]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled[0].start_time == time(7, 0)


def test_task_that_would_run_past_midnight_is_skipped():
    owner = Owner("Jordan", available_minutes=300, day_start=time(23, 30))
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Long walk", 60)]))
    plan = Scheduler(owner).generate_plan(DAY)
    assert plan.scheduled == [] and plan.skipped[0].reason == "No free slot left today."


def test_recurrence_crosses_year_end():
    assert Task("Walk", 30).mark_complete(date(2026, 12, 31)).due_date == date(2027, 1, 1)
    weekly = Task("Bath", 20, frequency="weekly")
    assert weekly.mark_complete(date(2026, 12, 28)).due_date == date(2027, 1, 4)


def test_overdue_task_is_still_due():
    task = Task("Bath", 20, due_date=DAY - timedelta(days=3))
    assert task.is_due(DAY)


def test_completing_same_task_twice_in_one_day_raises():
    owner = Owner("Jordan")
    owner.add_pet(Pet("Mochi", "dog", tasks=[Task("Walk", 30)]))
    scheduler = Scheduler(owner)
    scheduler.complete_task("Mochi", "Walk", DAY)
    with pytest.raises(ValueError):
        scheduler.complete_task("Mochi", "Walk", DAY)
    assert len(owner.pets[0].tasks) == 2  # done today + tomorrow's, no extra copy
