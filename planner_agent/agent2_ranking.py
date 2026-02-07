import os
import google.generativeai as genai
import json
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# API Key
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"response_mime_type": "application/json"}
    )

# Prompt 
SYSTEM_PROMPT = """
You are an expert Academic Difficulty Analyst. 
Your goal is to analyze course content to build a realistic study plan.

**CRITICAL: SCOPE ENFORCEMENT (THE "MIDTERM CUTOFF")**
You will receive text from multiple files (Syllabus, Midterm Overview).
You must enforce this hierarchy strictly:

1.  **TIER 1 (The Absolute Truth): "Midterm Overview" or "Exam Guide"**
    * IF you see a file header like `=== Midterm Overview.pdf ===`, **ONLY** schedule the topics explicitly listed in that file's "Coverage" section.
    * **DELETE RULE:** You must **DISCARD** any topic from the Syllabus that appears *after* the Midterm cutoff.
    * *Example:* If Midterm covers Ch 1-6, and Syllabus lists Ch 7 (Hydrogen Atom), **DO NOT INCLUDE CH 7.**

2.  **TIER 2 (Fallback): "Syllabus"**
    * ONLY use the full Syllabus list if *no* Midterm Overview file is provided.

**CRITICAL: RELATIVE DIFFICULTY SCALING**
You will be given a list of ALL courses the student is taking.
Compare the CURRENT course to that list.
1.  **If Current Course is the Hardest (e.g., Quantum Physics):**
    -   Target Total Hours: **25 - 40 hours**.
    -   Be generous with time estimates.
2.  **If Current Course is the Easiest (e.g., Intro Stats, Electives):**
    -   Target Total Hours: **10 - 15 hours**.
    -   Aggressively reduce time. Assume the student just needs to "Review" rather than "Learn".

**PRIORITY RULES:**
1.  **Scope:** STRICTLY follow the "Midterm Rule" above. Do not hallucinate extra chapters.
2.  **Volume:** If a topic covers multiple chapters (e.g. "Ch 1-5"), assign a block of 8-12 hours.
3.  **Multipliers:**
    -   Math/Physics/Systems: 1.5x (High Focus = true)
    -   Biology/Health/History: 0.7x (High Focus = false)

**OUTPUT FORMAT:**
{
  "topics": [
    {"topic": "Thermodynamics (Ch 1-3)", "est_hours": 8.0, "high_focus": true},
    {"topic": "History of Physics", "est_hours": 1.5, "high_focus": false}
  ]
}
"""

# This is the main function that runs, it will combine the user input + the giant prompt above
def analyze_course(course_name, structured_context, all_courses_list="None", user_constraints="None"):
    """
    Analyzes course text with RELATIVE AWARENESS and SCOPE ENFORCEMENT.
    """
    print(f"  -> Agent 2 (Ranker): Analyzing '{course_name}' with Scope Enforcement...")
    
    user_prompt = f"""
    CURRENT COURSE: {course_name}
    OTHER COURSES STUDENT IS TAKING: {all_courses_list}
    USER CONSTRAINTS: {user_constraints}
    
    FULL COURSE CONTEXT (Syllabus + Midterm Files):
    {structured_context[:60000]} 
    
    TASK: 
    1. Check for a "Midterm Overview" file. 
    2. If found, define the "Cutoff Chapter" (e.g., Chapter 6).
    3. **DISCARD** any Syllabus topic that is after that cutoff.
    4. Estimate hours based on Relative Difficulty (Hard/Medium/Easy).
    """
    
    max_retries = 3
    base_delay = 10 
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(SYSTEM_PROMPT + "\n" + user_prompt)
            data = json.loads(response.text)

            if isinstance(data, list):
                data = data[0]

            return data
        except Exception as e:
            if "429" in str(e):
                print(f"    ⚠️  Rate Limit Hit. Cooling down for {base_delay}s...")
                time.sleep(base_delay)
                base_delay *= 2 
            else:
                print(f"    ❌ Error in Agent 2: {e}")
                break

    return {"topics": [{"topic": f"Review {course_name}", "est_hours": 5, "high_focus": False}]}