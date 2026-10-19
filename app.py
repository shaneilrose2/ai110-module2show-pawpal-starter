from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

st.divider()

# --- Owner (kept in session_state so it survives reruns) ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
owner = st.session_state.owner

st.subheader("Owner")
col1, col2, col3 = st.columns(3)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = int(st.number_input(
        "Available minutes today", min_value=0, max_value=1440, value=owner.available_minutes
    ))
with col3:
    owner.day_start = st.time_input("Day starts at", value=owner.day_start)

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
                st.success(f"Added {pet_name.strip()}.")
            except ValueError as e:
                st.error(str(e))

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
        st.table([
            {
                "time": task.fixed_time.strftime("%H:%M") if task.fixed_time else "flexible",
                "pet": pet_of[id(task)].name,
                "task": task.title,
                "minutes": task.duration_minutes,
                "priority": task.priority.name.lower(),
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
        st.table([
            {
                "time": item.start_time.strftime("%H:%M"),
                "pet": item.pet.name,
                "task": item.task.title,
                "minutes": item.task.duration_minutes,
                "priority": item.task.priority.name.lower(),
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
        st.table([
            {"pet": item.pet.name, "task": item.task.title, "reason": item.reason}
            for item in plan.skipped
        ])
