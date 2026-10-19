from datetime import date, time
from pathlib import Path

import pandas as pd
import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, load_owner, save_owner

DATA_FILE = Path(__file__).parent / "pawpal_data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

PRIORITY_BADGE = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}
PRIORITY_COLOR = {
    "🔴 high": "background-color: rgba(255, 75, 75, 0.15)",
    "🟡 medium": "background-color: rgba(255, 193, 7, 0.15)",
    "🟢 low": "background-color: rgba(40, 167, 69, 0.15)",
}


def badge(priority: Priority) -> str:
    return PRIORITY_BADGE[priority.name.lower()]


def show_table(rows: list[dict]) -> None:
    """Show rows as a clean table; the priority column (if any) is color-coded."""
    df = pd.DataFrame(rows)
    if "priority" in df.columns:
        df = df.style.map(lambda v: PRIORITY_COLOR.get(v, ""), subset=["priority"])
    st.dataframe(df, hide_index=True)


st.title("🐾 PawPal+")

st.caption("Plan your pets' care around your day: priorities, fixed times and recurring tasks.")

with st.expander("How it works"):
    st.markdown(
        """
1. Set your **available time** and when your day starts.
2. Add your **pets**, then their **tasks** (duration, priority, how often, optional fixed time).
3. Click **Generate schedule**: fixed-time tasks are placed first, then the rest by priority
   until your time runs out. Every task shows *why* it was chosen or skipped.
"""
    )

st.divider()

# --- Owner: loaded from pawpal_data.json once per session, kept in session_state ---
if "owner" not in st.session_state:
    try:
        st.session_state.owner = load_owner(DATA_FILE) or Owner(name="Jordan")
    except (ValueError, KeyError) as e:  # includes json.JSONDecodeError
        st.warning(f"Couldn't read {DATA_FILE.name} ({e}); starting fresh.")
        st.session_state.owner = Owner(name="Jordan")
owner = st.session_state.owner


def save() -> None:
    """Auto-save after every change."""
    save_owner(owner, DATA_FILE)


st.subheader("Owner")
col1, col2, col3 = st.columns(3)
with col1:
    name = st.text_input("Owner name", value=owner.name)
with col2:
    minutes = int(st.number_input(
        "Available minutes today", min_value=0, max_value=1440, value=owner.available_minutes
    ))
with col3:
    day_start = st.time_input("Day starts at", value=owner.day_start)
if (name, minutes, day_start) != (owner.name, owner.available_minutes, owner.day_start):
    owner.name, owner.available_minutes, owner.day_start = name, minutes, day_start
    save()
st.caption(f"💾 Changes are saved automatically to `{DATA_FILE.name}`.")

# --- Add a pet ---
st.subheader("Add a Pet")
with st.form("add_pet_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Enter a pet name.")
        else:
            try:
                owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age)))
                save()
                st.success(f"Added {pet_name.strip()}.")
            except ValueError as e:
                st.error(str(e))

if owner.pets:
    show_table([
        {"pet": p.name, "species": p.species, "age": p.age, "tasks": len(p.tasks)}
        for p in owner.pets
    ])

# --- Add a task ---
st.subheader("Add a Task")
if not owner.pets:
    st.info("Add a pet first.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])
            task_title = st.text_input("Task title", value="Morning walk")
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
            has_fixed_time = st.checkbox("Must happen at a fixed time")
            fixed_time = st.time_input("Fixed time", value=time(8, 0))
        if st.form_submit_button("Add task"):
            if not task_title.strip():
                st.error("Enter a task title.")
            else:
                pet = next(p for p in owner.pets if p.name == pet_choice)
                pet.add_task(Task(
                    title=task_title.strip(),
                    duration_minutes=int(duration),
                    priority=Priority[priority.upper()],
                    frequency=frequency,
                    fixed_time=fixed_time if has_fixed_time else None,
                ))
                save()
                st.success(f"Added '{task_title.strip()}' for {pet.name}.")

# --- Current tasks: filtered and sorted by the Scheduler ---
today = date.today()
scheduler = Scheduler(owner)


def status_of(task: Task) -> str:
    if task.last_completed:
        return f"✅ done {task.last_completed:%b %d}"
    if task.due_date and task.due_date > today:
        return f"🗓️ due {task.due_date:%b %d}"
    return "⏳ to do"


st.subheader("Tasks")
if not owner.get_all_tasks():
    st.info("No tasks yet. Add one above.")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_filter = st.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets], key="pet_filter")
    with col2:
        status_filter = st.selectbox("Status", ["All", "To do", "Done today"], key="status_filter")
    with col3:
        sort_choice = st.selectbox("Sort by", ["Time", "Priority"], key="sort_choice")

    pairs = scheduler.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "To do": False, "Done today": True}[status_filter],
        on=today,
    )
    pet_of = {id(task): pet for pet, task in pairs}
    sort = scheduler.sort_by_time if sort_choice == "Time" else scheduler.sort_by_priority
    tasks = sort([task for _, task in pairs])

    if tasks:
        show_table([
            {
                "time": task.fixed_time.strftime("%H:%M") if task.fixed_time else "flexible",
                "pet": pet_of[id(task)].name,
                "task": task.title,
                "minutes": task.duration_minutes,
                "priority": badge(task.priority),
                "repeats": task.frequency,
                "status": status_of(task),
            }
            for task in tasks
        ])
        st.caption(f"Showing {len(tasks)} task(s), sorted by {sort_choice.lower()}.")
    else:
        st.info("No tasks match these filters.")

    # --- Mark a task complete ---
    due_today = scheduler.filter_tasks(completed=False, on=today)
    due_today = [(pet, task) for pet, task in due_today if task.is_due(today)]
    if due_today:
        with st.form("complete_form"):
            labels = [f"{pet.name}: {task.title}" for pet, task in due_today]
            choice = st.selectbox("Mark a task done", labels)
            if st.form_submit_button("Mark complete"):
                pet, task = due_today[labels.index(choice)]
                try:
                    next_task = scheduler.complete_task(pet.name, task.title, today)
                    save()
                    if next_task:
                        st.success(f"Completed {task.title} for {pet.name}. "
                                   f"Next one is due {next_task.due_date:%A, %B %d}.")
                    else:
                        st.success(f"Completed {task.title} for {pet.name}.")
                except ValueError as e:
                    st.warning(str(e))

st.divider()

# --- Build schedule ---
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    plan = scheduler.generate_plan(today)
    conflicts = scheduler.detect_conflicts(plan)
    used = sum(item.task.duration_minutes for item in plan.scheduled)

    if not plan.scheduled:
        st.warning("Nothing to schedule today.")
    else:
        st.success(
            f"Scheduled {len(plan.scheduled)} task(s) for {today:%A, %B %d}: "
            f"{used} of {owner.available_minutes} available minutes used."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scheduled", len(plan.scheduled))
        m2.metric("Minutes used", f"{used} / {owner.available_minutes}")
        m3.metric("Conflicts", len(conflicts))
        m4.metric("Skipped", len(plan.skipped))
        st.progress(min(used / owner.available_minutes, 1.0) if owner.available_minutes else 0.0)
        show_table([
            {
                "time": item.start_time.strftime("%H:%M"),
                "pet": item.pet.name,
                "task": item.task.title,
                "minutes": item.task.duration_minutes,
                "priority": badge(item.task.priority),
                "why": item.reason,
            }
            for item in plan.scheduled
        ])

    if conflicts:
        st.warning(f"⚠️ {len(conflicts)} time conflict(s). Consider moving one of these tasks:")
        for conflict in conflicts:
            st.warning(conflict)
    elif plan.scheduled:
        st.success("No time conflicts.")

    if plan.skipped:
        st.markdown("**Skipped today**")
        show_table([
            {"pet": item.pet.name, "task": item.task.title, "reason": item.reason}
            for item in plan.skipped
        ])
