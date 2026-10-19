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

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
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

# --- Current tasks across all pets ---
all_tasks = owner.get_all_tasks()
if all_tasks:
    st.write("Current tasks:")
    st.table([
        {
            "pet": pet.name,
            "task": task.title,
            "minutes": task.duration_minutes,
            "priority": task.priority.name.lower(),
            "frequency": task.frequency,
            "fixed time": task.fixed_time.strftime("%H:%M") if task.fixed_time else "",
        }
        for pet, task in all_tasks
    ])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# --- Build schedule ---
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    today = date.today()
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan(today)

    if not plan.scheduled:
        st.warning("Nothing to schedule today.")
    else:
        st.markdown(f"**Today's schedule ({today:%A, %B %d})**")
        st.table([
            {
                "time": item.start_time.strftime("%H:%M"),
                "pet": item.pet.name,
                "task": item.task.title,
                "minutes": item.task.duration_minutes,
                "why": item.reason,
            }
            for item in plan.scheduled
        ])
        used = sum(item.task.duration_minutes for item in plan.scheduled)
        st.caption(f"{used} of {owner.available_minutes} available minutes used.")

    for item in plan.skipped:
        st.warning(f"Skipped {item.task.title} ({item.pet.name}): {item.reason}")
    for warning in scheduler.detect_conflicts(plan):
        st.error(warning)
