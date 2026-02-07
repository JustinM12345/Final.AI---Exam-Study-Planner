import os
import json
import datetime
from google.adk.agents import Agent

# Importing the 4 agents
from .agent1_sorter import sort_files, extract_header_text
from .agent2_ranking import analyze_course
from .agent3_scheduler import generate_schedule
from .agent4_confirming import audit_schedule

# Handles the entire app process
def run_study_planner_tool(user_hints: str, user_constraints: str, end_date: str) -> str:
    print("\n🚀 [ADK] Starting Planner Workflow...")
    
    # Determining file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, '..'))
    
    files_dir = os.path.join(repo_root, 'uploaded_files')
    output_md_path = os.path.join(repo_root, 'final_study_plan.md')
    output_json_path = os.path.join(repo_root, 'final_study_plan.json')

    print(f"📂 Looking for files in: {files_dir}")

    if not os.path.exists(files_dir):
        return f"Error: The folder '{files_dir}' does not exist."

    pdf_files = [
        os.path.join(files_dir, f) 
        for f in os.listdir(files_dir) 
        if f.lower().endswith('.pdf')
    ]
    
    if not pdf_files:
        return f"Error: No PDF files found in {files_dir}."

    print(f"   -> Found {len(pdf_files)} PDFs.")
    
    # Ensure that the bot knows the correct date since during teseting it kept hallucinating dates
    start_date = datetime.date.today().strftime("%Y-%m-%d")
    is_valid_date = False

    if end_date:
        try:
            s = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            # Only accepts dates in the future
            if e > s:
                is_valid_date = True
            else:
                print(f"   ⚠️ Detected past/invalid end date ({end_date}). Ignoring.")
        except ValueError:
            print(f"   ⚠️ Malformed date format ({end_date}). Ignoring.")

    # If the Agent failed to give a valid date, we force a 14-day default here.
    if not is_valid_date:
        future_date = datetime.date.today() + datetime.timedelta(days=14)
        end_date = future_date.strftime("%Y-%m-%d")
        print(f"   🔄 Defaulting to 14-day plan: {end_date}")

    print(f"   🗓️ Planning Horizon: {start_date} to {end_date}")

    # Executing all 4 agents

    # (Agent 1) Sorting
    print("   -> Running Sorter...")
    sorted_courses = sort_files(pdf_files, user_hints)
    if not sorted_courses: return "Failed to sort files."

    # (Agent 2) Ranking
    print("   -> Running Ranker...")
    all_course_data = []
    course_list_str = ", ".join([c for c in sorted_courses.keys() if c != "General_Items"])
    
    for course_name, file_paths in sorted_courses.items():
        if course_name == "General_Items": continue
        
        structured_context = ""
        for path in file_paths:
            filename = os.path.basename(path)
            raw_text = extract_header_text(path) 
            structured_context += f"\n=== {filename} ===\n{raw_text}\n"

        difficulty = analyze_course(course_name, structured_context, course_list_str, user_constraints)
        all_course_data.append({"course": course_name, "analysis": difficulty})

    # (Agent 3 & 4) Feedback loop between the schedule maker and the confirmer
    print("   -> Entering Schedule/Audit Loop...")
    max_retries = 3
    attempt = 1
    is_valid = False
    current_constraints = user_constraints
    final_schedule = {}
    feedback = "Initial Run"

    while attempt <= max_retries and not is_valid:
        print(f"      Attempt {attempt}...")
        final_schedule = generate_schedule(all_course_data, start_date, end_date, current_constraints)
        is_valid, feedback = audit_schedule(final_schedule, current_constraints, all_course_data)
        
        if not is_valid:
            current_constraints += f" [CORRECTION: {feedback}]"
            attempt += 1

    # Markdown output
    markdown_output = f"# 📅 Final Exam Study Plan\n\n"
    markdown_output += f"### 🛡️ Auditor Report (Agent 4)\n"
    status_icon = "✅" if "approved" in feedback.lower() else "⚠️"
    markdown_output += f"> {status_icon} **STATUS:** {feedback}\n\n---\n"

    if not final_schedule.get("schedule"):
        markdown_output += "No schedule generated."
    else:
        for day_entry in final_schedule["schedule"]:
            date = day_entry.get("date", "Unknown")
            day_name = day_entry.get("day_name", "")
            
            markdown_output += f"## {day_name}, {date}\n"
            markdown_output += "| Time | Type | Task |\n| :--- | :--- | :--- |\n"
            
            for event in day_entry.get("events", []):
                t_time = event.get("time", "")
                t_task = event.get("task", "")
                t_type = event.get("type", "").upper()
                
                icon = "📚"
                if "BREAK" in t_type: icon = "☕"
                elif "MEAL" in t_type: icon = "🍽️"
                elif "PERSONAL" in t_type or "WAKE" in t_type: icon = "🛌"
                elif "REVIEW" in t_type: icon = "🧠"
                
                markdown_output += f"| **{t_time}** | {icon} {t_type} | {t_task} |\n"
            markdown_output += "\n---\n\n"

    # Saving generated outputs to files
    print(f"   -> Saving markdown to {output_md_path}...")
    with open(output_md_path, "w") as f:
        f.write(markdown_output)

    print(f"   -> Saving JSON to {output_json_path}...")
    with open(output_json_path, "w") as f:
        json.dump(final_schedule, f, indent=2)

    return markdown_output

# --- DEFINE THE ADK AGENT ---
root_agent = Agent(
    name="study_planner_agent",
    model="gemini-3-flash-preview", 
    description="A multi-agent system that plans study schedules from PDF textbooks.",
    tools=[run_study_planner_tool] 
)