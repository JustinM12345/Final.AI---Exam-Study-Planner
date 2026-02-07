import os
import google.generativeai as genai
import json
import datetime
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"response_mime_type": "application/json"}
    )

SYSTEM_PROMPT = """
You are an expert Time-Blocking Scheduler. 
Your goal is to fit ALL provided study tasks into the calendar.

**CRITICAL PRIORITY: COURSE COVERAGE**
1.  **YOU MUST SCHEDULE TASKS FOR EVERY SINGLE COURSE LISTED.** 2.  If a course (e.g., PHYS 234) is missing from the output, you have FAILED.
3.  It is better to squeeze the schedule (reduce breaks) than to skip a course.

**HIERARCHY OF RULES:**
1.  **USER CONSTRAINTS (MUST LISTEN TO AT ALL TIMES):** (e.g. "Wake up at 10am") -> Overrides everything.
2.  **MANDATORY CONTENT:** All courses must appear in the schedule.
3.  **REVIEW BUFFER:** No new content in the last 48 hours (Review Only).
4.  **BIOLOGICAL DEFAULTS:**
    -   **Sleep:** ~23:00 to 07:00.
    -   **Morning Routine:** 1 hour after waking (Label: "Morning Routine").
    -   **Meals:** Lunch (~12:00) and Dinner (~18:00).

**CHUNKING LOGIC:**
-   **Split Big Tasks:** If a task is > 2.5 hours, split it.
-   **Interleaving:** Mix subjects (e.g. Math then Reading).

**OUTPUT FORMAT:**
{
  "schedule": [
    {
        "date": "2026-02-24",
        "day_name": "Tuesday",
        "events": [
            {"time": "07:00 - 08:00", "task": "Morning Routine", "type": "personal"},
            {"time": "08:00 - 10:00", "task": "PHYS 234: Quantum States", "type": "study"},
            {"time": "12:00 - 13:00", "task": "LUNCH", "type": "meal"}
        ]
    }
  ]
}
"""

def generate_schedule(all_course_data, start_date, end_date, user_constraints="None"):
    print(f"  -> Agent 3 (Scheduler): Building plan from {start_date} to {end_date}...")
    
    # 1. Grabbing current date for context
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # 2. Prepare the Task List
    tasks_summary = ""
    for course_entry in all_course_data:
        c_name = course_entry['course']
        analysis = course_entry['analysis']
        if isinstance(analysis, list): analysis = analysis[0]
        
        topics = analysis.get('topics', [])
        
        tasks_summary += f"\nCOURSE: {c_name}\n"
        for t in topics:
            tasks_summary += f" - {t['topic']} (Need: {t['est_hours']}h) [High Focus: {t.get('high_focus')}]\n"

    # 3. Building final prompt
    user_prompt = f"""
    CURRENT DATE: {today}
    PLANNING RANGE: {start_date} to {end_date}
    
    *** USER CUSTOMIZATION ***:
    "{user_constraints}" 
    (NOTE: These constraints override your default sleep/meal times!)
    
    TASKS TO SCHEDULE:
    {tasks_summary}
    
    ACTION:
    Create the schedule. 
    CRITICAL: Ensure the last 2 days of the plan are 'Review Only' (The Review Buffer).
    """
    
    try:
        response = model.generate_content(SYSTEM_PROMPT + "\n" + user_prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"    ❌ Error in Scheduler: {e}")
        return {"schedule": []}