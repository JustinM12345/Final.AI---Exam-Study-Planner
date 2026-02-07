import os
import json
import re
import datetime
from google.adk.agents import Agent

# Import skills
from .agent1_sorter import sort_files, extract_header_text
from .agent2_ranking import analyze_course
from .agent3_scheduler import generate_schedule
from .agent4_confirming import audit_schedule

# Scans text for exam dates
def parse_dates_from_text(text, current_year):
    date_patterns = [
        r"Date:\s*([A-Za-z]+ \d{1,2}, \d{4})",  # Explicit Date with Year
        r"Date:\s*([A-Za-z]+ \d{1,2})",         # Date without Year
        r"Exam:\s*([A-Za-z]+ \d{1,2}, \d{4})"   # Exam Label
    ]
    
    found_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Handle "Month DD, YYYY"
                if "," in match:
                    dt = datetime.datetime.strptime(match, "%B %d, %Y").date()
                else:
                    # Handle "Month DD" (Assume current year)
                    dt = datetime.datetime.strptime(f"{match}, {current_year}", "%B %d, %Y").date()
                found_dates.append(dt)
            except:
                pass
                
    if found_dates:
        return max(found_dates)
    return None

# The function that runs the study planner
def run_study_planner_tool(user_hints: str, user_constraints: str, end_date: str) -> str:
    print("\n🚀 [ADK] Starting Planner Workflow...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, '..'))
    files_dir = os.path.join(repo_root, 'uploaded_files')
    output_md_path = os.path.join(repo_root, 'final_study_plan.md')
    output_json_path = os.path.join(repo_root, 'final_study_plan.json')

    if not os.path.exists(files_dir):
        return f"Error: '{files_dir}' not found."

    pdf_files = [os.path.join(files_dir, f) for f in os.listdir(files_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return f"Error: No PDFs found in {files_dir}."

    print(f"📂 Found {len(pdf_files)} PDFs. Proceeding...")

    # Fixes date
    today = datetime.date.today()
    current_year = today.year
    start_date = today.strftime("%Y-%m-%d")
    is_valid = False
    
    # Track the target date object for comparison later
    target_date = None

    if end_date:
        try:
            s = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            if e > s: 
                is_valid = True
                target_date = e.date()
        except: pass

    if not is_valid:
        target_date = today + datetime.timedelta(days=14)
        end_date = target_date.strftime("%Y-%m-%d")
        print(f"   🗓️  Date Auto-Fix: Defaulting to 14-day plan ({end_date})")
    else:
        print(f"   🗓️  Planning Horizon: {start_date} to {end_date}")

    # Agents

    # Agent 1: Sorter
    print("   🔍 Agent 1: Scanning & Sorting files...")
    sorted_courses = sort_files(pdf_files, user_hints)
    if not sorted_courses: return "Failed to sort files."

    # Agent 2: Analyst
    print("   🧠 Agent 2: Analyzing Course Difficulty...")
    all_course_data = []
    course_list_str = ", ".join([c for c in sorted_courses.keys() if c != "General_Items"])
    
    # Progress Counter
    total_courses = len([c for c in sorted_courses if c != "General_Items"])
    count = 1
    
    latest_exam_date = None # Track the latest exam found
    
    for course_name, file_paths in sorted_courses.items():
        if course_name == "General_Items": continue
        
        print(f"      [{count}/{total_courses}] Reading {course_name}...", end="", flush=True)
        
        structured_context = ""
        for path in file_paths:
            raw_text = extract_header_text(path) 
            structured_context += f"\n=== {os.path.basename(path)} ===\n{raw_text}\n"

            # Date scanning logic
            found = parse_dates_from_text(raw_text, current_year)
            if found:
                if latest_exam_date is None or found > latest_exam_date:
                    latest_exam_date = found

        difficulty = analyze_course(course_name, structured_context, course_list_str, user_constraints)
        all_course_data.append({"course": course_name, "analysis": difficulty})
        print(" Done.")
        count += 1

    # --- NEW: Auto-Extend Schedule if Exam Found ---
    if latest_exam_date and latest_exam_date > target_date:
        print(f"\n   ⚠️  Auto-Extending Schedule to cover Exam on {latest_exam_date}!")
        target_date = latest_exam_date
        end_date = target_date.strftime("%Y-%m-%d") # Update string for scheduler
        
    print(f"   🎯 Final Planning Range: {start_date} to {end_date}")

    # Agent 3 and 4 feedback look
    print("   🗓️  Agent 3 & 4: Generating Schedule...")
    max_retries = 3
    attempt = 1
    is_valid = False
    current_constraints = user_constraints
    final_schedule = {}
    feedback = "Initial Run"

    while attempt <= max_retries and not is_valid:
        print(f"      Attempt {attempt}/{max_retries}: Drafting...", end="", flush=True)
        final_schedule = generate_schedule(all_course_data, start_date, end_date, current_constraints)
        
        print(" Auditing...", end="", flush=True)
        is_valid, feedback = audit_schedule(final_schedule, current_constraints, all_course_data)
        
        if not is_valid:
            print(f" ❌ Rejected.")
            current_constraints += f" [CORRECTION: {feedback}]"
            attempt += 1
        else:
            print(f" ✅ Approved!")

    # Output
    markdown_output = f"# 📅 Final Exam Study Plan\n\n### 🛡️ Auditor Report: {feedback}\n\n---\n"
    
    if final_schedule.get("schedule"):
        for day in final_schedule["schedule"]:
            markdown_output += f"## {day.get('day_name')}, {day.get('date')}\n"
            markdown_output += "| Time | Task |\n| :--- | :--- |\n"
            for e in day.get("events", []):
                markdown_output += f"| **{e.get('time')}** | {e.get('task')} |\n"
            markdown_output += "\n---\n"

    # Save to Disk
    with open(output_md_path, "w") as f: f.write(markdown_output)
    with open(output_json_path, "w") as f: json.dump(final_schedule, f, indent=2)

    print(f"\n✅ DONE! Saved to: {output_md_path}")
    return markdown_output

# --- AGENT DEFINITION ---
root_agent = Agent(
    name="study_planner_agent",
    model="gemini-2.0-flash", 
    description="Study Planner Tool",
    tools=[run_study_planner_tool] 
)