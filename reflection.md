# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**
Core actions a user should be able to perform:
1. Add pet
2. Feed pet
3. View tasks
4. Add tasks

- Briefly describe your initial UML design.
Initially, the UML had four classes: task, scheduler, pet and owner, where owner "has-a" pet, scheduler creates tasks, a pet needs a task and a task has priority.

- What classes did you include, and what responsibilities did you assign to each?
**DailyPlan** is the output of the Scheduler. It displays the collection of tasks that are for that day, including the tasks that were skipped and why via explain().
**ScheduledTask** is a task scheduled for that day which includes the start time, the pet assigned and reason the task was scheduled.
**Priority** is enumerated and is limited to low, medium and high, which helps limit typos.
**Task** is the general objective that needs to be completed. It has duration, frequency, priority and a boolean to show completion.
**Owner** is responsible for the pet(s). They have limited availablitity, can add pets and view all tasks.
**Scheduler** reads pets and tasks from owner in order to create a DailyPlan. It can prioritize tasks, detect conflicts and ensure the owners availabiltty can support the duration of the task(s). 
**Pet** has name, age and species. It can add and remove tasks associated with it. 


**b. Design changes**

- Did your design change during implementation? **Yes**
- If yes, describe at least one change and why you made it.
- **day_start:** the scheduler needed a start time to work out when each task happens.
- **get_all_tasks()** returns **(pet, task) pairs:** each scheduled task knows its pet, this avoids a Task → Pet → Task loop.
- **last_completed instead of completed:** a done/not-done flag never resets, repeated tasks were not recurring.
- **is_due(on), mark_complete(on), generate_plan(on):** recurring logic and plans need to know which date they're for.
- **fixed_time:** with tasks only placed back-to-back, nothing could overlap. Fixed-time tasks give *detect_conflicts* something real to check.
- **SkippedTask:** explain() must say why a task was left out and for which pet.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
The scheduler considers: whether a task is due that day (and its possible recurrence), fixed times (e.g. meds at 08:00), task priority, the owner's total available minutes, and the owner's day start time so tasks don't overlap.
- How did you decide which constraints mattered most?
Fixed-time tasks come first then priority comes next, so essential care is never pushed out by optional tasks. Available time is a hard limit and preferences matter least since they affect convenience and not the pet's wellbeing. Skipped tasks roll over to the next day since they are still due.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
A long high-priority task can extrude several shorter low-priority ones. The scheduler is greedy.
- Why is that tradeoff reasonable for this scenario?
Higher priority tasks such as administering medication, feeding, etc, should always replace optional tasks which can be skipped and rolled over to the next day.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project? 
I used AI throughout my entire workflow in order to help with design brainstorming, debugging and refactoring.
- What kinds of prompts or questions were most helpful?
Specific requests that named the class or method, e.g. “implement Owner and Scheduler using the UML” or “what edge cases should I test?” Asking "why" was also helpful.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
When the AI found the task double-completion bug, I chose which fix to apply rather than accepting its default.

- How did you evaluate or verify what the AI suggested?
I ran pytest and main.py, tested the app by hand, and compared the code against the UML.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
Sorting (priority and time), filtering (by pet and status), staying within available time, conflict detection, recurring tasks, and invalid input.

- Why were these tests important?
They prove the scheduler's decisions follow the rules and let me change code safely. Edge-case tests caught a real bug: completing a task twice in one day skipped the next day's task.

**b. Confidence**

- How confident are you that your scheduler works correctly?
4.5/5. All features are tested and pass.

- What edge cases would you test next if you had more time?
Fixed-time tasks that exceed the available time and late completions of recurring tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
Building and testing the scheduling logic in pawpal_system.py

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
Letting the owner walk multiple pets at once when their walk times overlap.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
I’m the architect when building with AI, so I must understand what it produces and how it works. I must not take everything at face value because it is cable of making grand mistakes.