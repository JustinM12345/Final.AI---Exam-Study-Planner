import os
import google.generativeai as genai
import json
import datetime
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview")

SYSTEM_PROMPT = """
You are an expert Time-Blocking Scheduler. 
Your goal is to fit ALL provided study tasks into the calendar.

**CRITICAL PRIORITY 1: BIOLOGICAL SKELETON (MANDATORY)**
Every single day object in your JSON output **MUST** explicitly include these 4 anchors. 
**DO NOT SKIP THEM TO SAVE SPACE, EVEN ON THE LAST DAY.**
1.  **Morning Routine:** (e.g., 10:00 - 11:00)
2.  **LUNCH:** (e.g., 12:00 - 13:00)
3.  **DINNER:** (e.g., 18:00 - 19:00)
4.  **SLEEP:** (e.g., 01:00)

**CRITICAL PRIORITY 2: COURSE COVERAGE**
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
            {"time": "12:00 - 13:00", "task": "LUNCH", "type": "meal"},
            {"time": "01:00", "task": "SLEEP", "type": "personal"}
        ]
    }
  ]
}
"""

def generate_schedule(all_course_data, start_date, end_date, user_constraints="None"):
    print(f"  -> Agent 3 (Scheduler): Building plan from {start_date} to {end_date}...")
    
    # 1. Calculate Duration (To prevent the 1-day cram bug)
    try:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        days_available = (end_dt - start_dt).days + 1
    except ValueError:
        days_available = 14 # Fallback default
    
    # 2. Prepare the Task List
    tasks_summary = ""
    total_est_hours = 0
    
    for course_entry in all_course_data:
        c_name = course_entry['course']
        analysis = course_entry['analysis']
        if isinstance(analysis, list): analysis = analysis[0]
        
        topics = analysis.get('topics', [])
        tasks_summary += f"\nCOURSE: {c_name}\n"
        for t in topics:
            h = t.get('est_hours', 1)
            total_est_hours += h
            tasks_summary += f" - {t['topic']} (Need: {h}h) [High Focus: {t.get('high_focus')}]\n"

    # --- LOGIC INJECTION: The "Safety Valve" ---
    # This checks if the math is impossible before asking the AI.
    daily_avg = total_est_hours / max(1, days_available)
    safety_instruction = ""
    
    if daily_avg > 9:
        print(f"    ⚠️  Workload Alert: {daily_avg:.1f} hours/day required. Injecting strict limits.")
        safety_instruction = f"""
        **⚠️ CRITICAL RESOURCE WARNING ⚠️**
        The user has {total_est_hours} hours of work but only {days_available} days.
        This averages to {daily_avg:.1f} hours/day, which is physically impossible without burnout.
        
        **UPDATED STRATEGY:**
        1.  **CAP DAILY STUDY AT 9 HOURS MAX.** Do not schedule more, even if tasks are left over.
        2.  **Triaging:** Prioritize 'High Focus' tasks. 
        3.  **Review Tasks:** Cut 'Review' time in half to save space.
        """

    # 3. Building final prompt (Your Original + The Safety Instruction)
    user_prompt = f"""
    CURRENT DATE: {start_date}
    PLANNING RANGE: {start_date} to {end_date} ({days_available} days)
    
    *** USER CUSTOMIZATION ***:
    "{user_constraints}" 
    (NOTE: These constraints override your default sleep/meal times!)
    
    TASKS TO SCHEDULE:
    {tasks_summary}
    
    {safety_instruction}
    
    ACTION:
    Create the schedule. 
    CRITICAL: Ensure the last 2 days of the plan are 'Review Only' (The Review Buffer).
    **MANDATORY:** You MUST include Morning Routine, Lunch, Dinner, and Sleep for EVERY DAY from Day 1 to Day {days_available}. Do not get lazy at the end.
    """
    
    try:
        response = model.generate_content(SYSTEM_PROMPT + "\n" + user_prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        else:
            return json.loads(text) # Attempt direct parse
            
    except Exception as e:
        print(f"    ❌ Error in Scheduler: {e}")
        return {"schedule": []}