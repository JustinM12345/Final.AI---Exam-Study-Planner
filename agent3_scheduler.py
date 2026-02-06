import os
import google.generativeai as genai
import json
import datetime
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # Using the smart model to handle complex logic
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"response_mime_type": "application/json"}
    )

SYSTEM_PROMPT = """
You are an expert Time-Blocking Scheduler. 
Your goal is to create a realistic, personalized itinerary that respects the user's biology and exam deadlines.

**HIERARCHY OF RULES (Follow in Order):**
1.  **USER CONSTRAINTS (HIGHEST PRIORITY):** If the user specifies "Dinner at 5pm" or "Wake up at 10am", YOU MUST OBEY. These override all default rules below.
2.  **THE "REVIEW BUFFER" RULE (Critical):** -   Identify the Exam Date (or the end of the planning range).
    -   **ALL** "New Learning" (Chapters, Topics) must be finished **48 HOURS BEFORE** the exam.
    -   The final 48 hours must be reserved EXCLUSIVELY for "Full Practice Exams", "Review", and "Cheat Sheet Prep".
    -   *Never* schedule a new chapter the day before an exam.
3.  **BIOLOGICAL DEFAULTS (Apply unless overridden):**
    -   **Sleep:** Default = 23:00 to 07:00. (Adjust if user mentions "Night Owl").
    -   **Lunch:** Default = 12:00 (1 hour).
    -   **Dinner:** Default = 18:00 (1 hour).
    -   **Breaks:** 10-min break after every 1.5 - 2 hours of work.

**CHUNKING LOGIC:**
-   **Split Big Tasks:** If a task is > 2.5 hours, split it: "Quantum Mechanics (Part 1)" -> Break -> "Quantum Mechanics (Part 2)".
-   **Interleaving:** Don't do 8 hours of Math. Mix "Math" with "Reading" or "Review" to keep the brain fresh.

**OUTPUT FORMAT:**
{
  "schedule": [
    {
        "date": "2026-02-24",
        "day_name": "Tuesday",
        "events": [
            {"time": "10:00 - 12:00", "task": "SYSD 300: Final Review (Buffer Zone)", "type": "review"},
            {"time": "12:00 - 13:00", "task": "LUNCH", "type": "meal"},
            {"time": "13:00 - 15:00", "task": "PHYS 234: Practice Problems", "type": "study"}
        ]
    }
  ]
}
"""

def generate_schedule(all_course_data, start_date, end_date, user_constraints="None"):
    print(f"  -> Agent 3 (Scheduler): Building plan from {start_date} to {end_date}...")
    
    # 1. Get Today's Date for context
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # 2. Prepare the Task List
    tasks_summary = ""
    for course_entry in all_course_data:
        c_name = course_entry['course']
        analysis = course_entry['analysis']
        # Fix for the List vs Dict bug
        if isinstance(analysis, list): analysis = analysis[0]
        
        topics = analysis.get('topics', [])
        
        tasks_summary += f"\nCOURSE: {c_name}\n"
        for t in topics:
            tasks_summary += f" - {t['topic']} (Need: {t['est_hours']}h) [High Focus: {t.get('high_focus')}]\n"

    # 3. Build the Prompt
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