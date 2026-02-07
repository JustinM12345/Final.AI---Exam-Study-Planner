import os
import json
import datetime

# --- IMPORTS ---
from agent1_sorter import sort_files, extract_header_text
from agent2_ranking import analyze_course
from agent3_scheduler import generate_schedule

def save_as_markdown(schedule_data, filename="final_study_plan.md"):
    """
    Converts the JSON schedule into a pretty Markdown table.
    """
    with open(filename, "w") as f:
        f.write("# 📅 Final Exam Study Plan\n\n")
        
        if "schedule" not in schedule_data:
            f.write("No schedule generated.")
            return

        for day_entry in schedule_data["schedule"]:
            date = day_entry.get("date", "Unknown Date")
            day_name = day_entry.get("day_name", "")
            
            # Day Header
            f.write(f"## {day_name}, {date}\n")
            
            # Table Header
            f.write("| Time | Type | Task |\n")
            f.write("| :--- | :--- | :--- |\n")
            
            # Rows
            for event in day_entry.get("events", []):
                time = event.get("time", "")
                task = event.get("task", "")
                type_ = event.get("type", "").upper()
                
                # Add an icon based on type
                icon = "📚"
                if "BREAK" in type_: icon = "☕"
                elif "MEAL" in type_: icon = "🍽️"
                elif "PERSONAL" in type_: icon = "🛌"
                elif "REVIEW" in type_: icon = "🧠"
                
                f.write(f"| **{time}** | {icon} {type_} | {task} |\n")
            
            f.write("\n---\n\n")
            
    print(f"✅ SUCCESS! Plan saved to '{filename}' (Markdown format).")

def main():
    print("\n===========================================")
    print("   🎓  FINAL.AI - FULL SYSTEM RUN  🎓")
    print("===========================================\n")
    
    # --- STEP 0: SETUP ---
    files_dir = "uploaded_files" 
    
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
        print(f"📂 Created folder '{files_dir}'. Put PDFs inside and run again.")
        return

    pdf_files = [os.path.join(files_dir, f) for f in os.listdir(files_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"⚠️  No PDFs found in '{files_dir}'!")
        return

    # --- STEP 1: USER INPUT ---
    print("--- 🤖 CONFIGURATION ---")
    
    user_input = input("1. User Hints (e.g. 'MATH 136' or enter to skip): ")
    user_hints = user_input if user_input.strip() != "" else None

    print("2. Personal Constraints (e.g. 'I wake up at 11am', 'No Fridays'):")
    user_constraints = input("   > ")
    if user_constraints.strip() == "":
        user_constraints = "None"

    default_end = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    end_date = input(f"3. Target End Date (YYYY-MM-DD) [Default: {default_end}]: ")
    if end_date.strip() == "":
        end_date = default_end
    
    start_date = datetime.date.today().strftime("%Y-%m-%d")

    # --- STEP 2: RUN AGENT 1 (Sort Files) ---
    print("\n🚀 AGENT 1: Sorting Files...")
    sorted_courses = sort_files(pdf_files, user_hints)
    
    if not sorted_courses:
        print("❌ No courses identified.")
        return
        
    print(f"   -> Identified {len(sorted_courses)} categories.")

    # --- STEP 3: RUN AGENT 2 (Analyze Difficulty) ---
    print("\n🧠 AGENT 2: Analyzing Content & Estimating Time...")
    
    all_course_data = []
    course_list_str = ", ".join([c for c in sorted_courses.keys() if c != "General_Items"])
    
    for i, (course_name, file_paths) in enumerate(sorted_courses.items()):
        if course_name == "General_Items":
            continue 
            
        print(f"  -> Processing Course: {course_name} ({len(file_paths)} files)")
        
        structured_context = ""
        for path in file_paths:
            filename = os.path.basename(path)
            raw_text = extract_header_text(path)
            structured_context += f"\n\n=== START OF DOCUMENT: {filename} ===\n"
            structured_context += raw_text
            structured_context += f"\n=== END OF DOCUMENT: {filename} ===\n"

        difficulty_data = analyze_course(course_name, structured_context, course_list_str, user_constraints)
        
        all_course_data.append({
            "course": course_name,
            "analysis": difficulty_data
        })

    # --- STEP 4: RUN AGENT 3 (The Scheduler) ---
    print(f"\n🗓️  AGENT 3: Building Calendar ({start_date} to {end_date})...")
    
    final_schedule = generate_schedule(all_course_data, start_date, end_date, user_constraints)
    
    # --- STEP 5: SAVE RESULTS (JSON + MARKDOWN) ---
    print("\n💾 Saving Study Plan...")
    
    # 1. Save Raw JSON (Good for debugging)
    with open("final_study_plan.json", "w") as f:
        json.dump(final_schedule, f, indent=2)

    # 2. Save Markdown (MEETS REQUIREMENT)
    save_as_markdown(final_schedule, "final_study_plan.md")
    
    # Optional: Preview
    if "schedule" in final_schedule and len(final_schedule["schedule"]) > 0:
        first_day = final_schedule["schedule"][0]
        print(f"\n👀 PREVIEW (Day 1 - {first_day.get('date')}):")
        for event in first_day.get('events', []):
            print(f"   - [{event.get('time')}] {event.get('task')}")
    else:
        print("⚠️ Warning: Schedule appears empty.")

if __name__ == "__main__":
    main()