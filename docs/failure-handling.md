# Failure handling (concise)

Behavior is implemented primarily in **`src/task_agent/agent/executor.py`** with **`ToolStatus`** / **`FailureReason`** from **`domain/models.py`**.

| Situation | Typical outcome |
|-----------|------------------|
| **Missing information** | `CLARIFICATION` with `MissingField` questions; no tools until resolved (e.g. dentist without city). |
| **No search results** | `PARTIAL_SUCCESS` or blocked path with blockers such as “No matching results” / “No booking was made” and a short hint to relax constraints. |
| **Temporary tool failure** | `FAILURE` (or blocked) with “Temporary tool failure. Please try again.” Booking retry: pending options can remain for transient booking errors. |
| **Unavailable booking** | `BLOCKED` / failure on `booking_service`; no reminder; clear messaging, no false success. |
| **Reminder fails after booking** | `PARTIAL_SUCCESS`: `booked_item` set, `reminder` null, blockers mention reminder failure. |
| **Unknown / vague request** | `BLOCKED`, examples in message, **no tools**. |
| **Cancel / pivot / constraint update** | Pending cleared or merged request replanned; see Phase 6 helpers in **`planner_support.py`** (`is_cancel_message`, `merge_constraint_update`, `is_new_standalone_task`). |

Tests: **`tests/test_failure_handling.py`**, **`tests/test_constraint_updates.py`**, **`tests/test_agent_execution.py`**.
