"""Demo script: build an owner with two pets, sort and filter tasks, and print today's schedule."""

from datetime import date, datetime, time, timedelta

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def print_tasks(heading: str, pairs) -> None:
    print(f"\n{heading}")
    print("-" * 60)
    if not pairs:
        print("  (none)")
    for pet, task in pairs:
        when = task.fixed_time.strftime("%H:%M") if task.fixed_time else "flexible"
        done = "done" if task.last_completed == date.today() else "to do"
        print(f"  {when:<9} {pet.name:<8} {task.title:<18} [{task.priority.name.lower()}, {done}]")


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(7, 30))

    mochi = Pet(name="Mochi", species="dog", age=3)
    biscuit = Pet(name="Biscuit", species="cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    # Added out of order on purpose, to show sort_by_time().
    biscuit.add_task(Task("Litter box", 10, Priority.MEDIUM, category="general", fixed_time=time(18, 0)))
    mochi.add_task(Task("Brushing", 15, Priority.LOW, category="grooming"))
    biscuit.add_task(Task("Breakfast", 10, Priority.HIGH, category="feeding", fixed_time=time(9, 0)))
    mochi.add_task(Task("Evening walk", 30, Priority.MEDIUM, category="walk", fixed_time=time(17, 30)))
    mochi.add_task(Task("Heartworm pill", 5, Priority.HIGH, category="meds", fixed_time=time(8, 0)))
    biscuit.add_task(Task("Feather toy play", 20, Priority.MEDIUM, category="enrichment"))
    mochi.add_task(Task("Morning walk", 30, Priority.HIGH, category="walk"))

    today = date.today()
    scheduler = Scheduler(owner)

    # Mark one task done so the completion filter has something to show.
    scheduler.complete_task("Mochi", "Heartworm pill", today)

    # --- Sorting ---
    all_pairs = owner.get_all_tasks()
    print_tasks("All tasks (unsorted, as stored on each pet)", all_pairs)

    pet_of = {id(task): pet for pet, task in all_pairs}
    by_time = scheduler.sort_by_time([task for _, task in all_pairs])
    print_tasks("Sorted by time (sort_by_time)", [(pet_of[id(t)], t) for t in by_time])

    # --- Filtering ---
    print_tasks("Only Biscuit's tasks (filter_tasks pet_name='Biscuit')",
                scheduler.filter_tasks(pet_name="Biscuit"))
    print_tasks("Completed today (filter_tasks completed=True)",
                scheduler.filter_tasks(completed=True))
    print_tasks("Mochi's tasks still to do (pet_name='Mochi', completed=False)",
                scheduler.filter_tasks(pet_name="Mochi", completed=False))

    # --- Today's schedule ---
    plan = scheduler.generate_plan(today)

    print(f"\nToday's Schedule for {owner.name} ({today:%A, %B %d})")
    print("=" * 60)
    for item in plan.scheduled:
        start = datetime.combine(today, item.start_time)
        end = start + timedelta(minutes=item.task.duration_minutes)
        print(f"{start:%H:%M}-{end:%H:%M}  {item.pet.name:<8} {item.task.title:<18} "
              f"[{item.task.priority.name.lower()}]")
        print(f"             -> {item.reason}")

    if plan.skipped:
        print("\nSkipped:")
        for item in plan.skipped:
            print(f"  {item.pet.name:<8} {item.task.title:<18} -> {item.reason}")

    for warning in scheduler.detect_conflicts(plan):
        print(f"\nWarning: {warning}")

    used = sum(item.task.duration_minutes for item in plan.scheduled)
    print(f"\nTotal: {used} of {owner.available_minutes} available minutes used.")


if __name__ == "__main__":
    main()
