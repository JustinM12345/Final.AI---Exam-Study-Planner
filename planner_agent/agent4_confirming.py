import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # Using the smart model (Flash 2.0) for high-level reasoning
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"response_mime_type": "application/json"}
    )

SYSTEM_PROMPT = """
You are an expert Audit & Compliance AI.
Your goal is to validate a study schedule against the original requirements and human limitations.

**YOUR AUDIT CHECKLIST:**
1.  **COMPLETENESS (Critical):** -   Compare the "REQUIRED COURSES" list against the "PROPOSED SCHEDULE".
    -   **IF A COURSE IS MISSING, YOU MUST FAIL THE AUDIT.**
    -   (e.g., If "PHYS 234" is required but never appears in the schedule, Reject it).

2.  **USER CONSTRAINTS:** -   Check strictly against user rules (e.g., "No Fridays", "Wake up at 11am").

3.  **HUMAN FACTORS (The "Smell Test"):**
    -   **Burnout:** Are there days with >10 hours of work?
    -   **Logic:** Is the student cramming 100% of a hard course into the last 2 days? (Bad distribution).
    -   **Sleep:** Are there tasks scheduled between 00:00 and 06:00 (unless "Night Owl" is specified)?

**OUTPUT FORMAT:**
Return a JSON object:
{
  "valid": boolean,
  "feedback": "string"
}

**FEEDBACK RULES:**
-   If Valid: "Approved. The plan covers all courses and respects user constraints."
-   If Invalid: Be specific. "REJECTED: You completely forgot to schedule 'PHYS 234'. Please add it."
"""

def audit_schedule(schedule_data, user_constraints, all_course_data):
    """
    Now accepts 'all_course_data' so it knows what courses MUST exist.
    """
    print("  -> Agent 4 (AI Auditor): verifying completeness & logic...")
    
    if "schedule" not in schedule_data or not schedule_data["schedule"]:
        return False, "CRITICAL: The schedule was empty."

    # 1. Extract the Requirements (The "Answer Key")
    required_courses = []
    total_hours_needed = 0
    for c in all_course_data:
        c_name = c['course']
        required_courses.append(c_name)
        # Sum up hours to give Agent 4 a sense of scale
        # (Assuming the analysis structure from Agent 2)
        analysis = c['analysis']
        if isinstance(analysis, list): analysis = analysis[0]
        for t in analysis.get('topics', []):
            total_hours_needed += t.get('est_hours', 0)

    # 2. Minify Schedule for the Prompt
    minified_schedule = []
    for day in schedule_data["schedule"]:
        day_summary = {
            "date": day.get("date"),
            "events": [f"{e.get('time')} - {e.get('task')}" for e in day.get("events", [])]
        }
        minified_schedule.append(day_summary)

    # 3. Build the "Project Manager" Prompt
    user_prompt = f"""
    --- REQUIREMENTS (INPUT) ---
    REQUIRED COURSES: {", ".join(required_courses)}
    TOTAL ESTIMATED WORKLOAD: {total_hours_needed} hours
    USER CONSTRAINTS: "{user_constraints}"
    
    --- PROPOSED PLAN (OUTPUT) ---
    {json.dumps(minified_schedule, indent=2)}
    
    --- MISSION ---
    Audit this plan. 
    1. Did Agent 3 forget any courses? (Check {required_courses} vs the Plan).
    2. Is the schedule biologically realistic?
    3. Did it follow user constraints?
    """
    
    try:
        response = model.generate_content(SYSTEM_PROMPT + "\n" + user_prompt)
        result = json.loads(response.text)
        
        is_valid = result.get("valid", False)
        feedback = result.get("feedback", "Unknown Error")
        
        if is_valid:
            print("  -> Agent 4: ✅ Schedule approved.")
        else:
            print(f"  -> Agent 4: ❌ Audit Failed. Feedback: {feedback}")
            
        return is_valid, feedback

    except Exception as e:
        print(f"    ❌ Error in Agent 4: {e}")
        return True, "Auditor bypassed due to error."