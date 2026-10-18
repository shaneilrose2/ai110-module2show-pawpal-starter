"""Demo script: build an owner with two pets and print today's schedule."""

from datetime import date, datetime, time, timedelta

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(7, 30))

    mochi = Pet(name="Mochi", species="dog", age=3)
    biscuit = Pet(name="Biscuit", species="cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(biscuit)

    mochi.add_task(Task("Morning walk", 30, Priority.HIGH, category="walk"))
    mochi.add_task(Task("Heartworm pill", 5, Priority.HIGH, category="meds", fixed_time=time(8, 0)))
    mochi.add_task(Task("Brushing", 15, Priority.LOW, category="grooming"))
    biscuit.add_task(Task("Breakfast", 10, Priority.HIGH, category="feeding", fixed_time=time(9, 0)))
    biscuit.add_task(Task("Feather toy play", 20, Priority.MEDIUM, category="enrichment"))
    biscuit.add_task(Task("Litter box", 10, Priority.MEDIUM, category="general", fixed_time=time(18, 0)))

    today = date.today()
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(today)

    print(f"Today's Schedule for {owner.name} ({today:%A, %B %d})")
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
