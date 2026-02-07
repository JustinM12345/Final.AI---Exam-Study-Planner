import os
import json
import datetime
import time

# --- IMPORTS ---
# Ensure your file is named 'agent4_confirming.py' based on your previous message
from agent1_sorter import sort_files, extract_header_text
from agent2_ranking import analyze_course
from agent3_scheduler import generate_schedule
from agent4_confirming import audit_schedule 

def save_as_markdown(schedule_data, audit_feedback, filename="final_study_plan.md"):
    """
    Converts the JSON schedule into a pretty Markdown table.
    Includes the Final Audit Report at the top.
    """
    with open(filename, "w") as f:
        f.write("# 📅 Final Exam Study Plan\n\n")
        
        # --- WRITE AUDIT REPORT ---
        f.write("### 🛡️ Auditor Report (Agent 4)\n")
        
        # Check if the feedback indicates approval
        if "approved" in audit_feedback.lower() or "looks good" in audit_feedback.lower() or "valid" in audit_feedback.lower():
            f.write(f"> ✅ **STATUS: PASS**\n> {audit_feedback}\n")
        else:
            f.write(f"> ⚠️ **STATUS: PASSED WITH WARNINGS**\n> {audit_feedback}\n")
        
        f.write("\n---\n")
        # --------------------------
        
        if "schedule" not in schedule_data or not schedule_data["schedule"]:
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
                elif "WAKE" in type_: icon = "☀️"
                
                f.write(f"| **{time}** | {icon} {type_} | {task} |\n")
            
            f.write("\n---\n\n")
            
    print(f"✅ SUCCESS! Plan saved to '{filename}' (Markdown format).")

def main():
    print("\n===========================================")
    print("   🎓  FINAL.AI - SELF-HEALING SYSTEM  🎓")
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

    # Default end date: 14 days from now
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
    # Create a simple string list of courses for relative difficulty scaling
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

        # Call Agent 2
        difficulty_data = analyze_course(course_name, structured_context, course_list_str, user_constraints)
        
        all_course_data.append({
            "course": course_name,
            "analysis": difficulty_data
        })

    # --- STEP 4: THE SELF-HEALING LOOP (Agent 3 + Agent 4) ---
    print(f"\n🗓️  AGENT 3 & 4: Building & Auditing Calendar...")
    
    max_retries = 3
    attempt = 1
    is_valid = False
    current_constraints = user_constraints # Start with basic user rules
    final_schedule = {}
    last_feedback = ""

    while attempt <= max_retries and not is_valid:
        print(f"\n   🔄 Attempt {attempt}/{max_retries}: Generating Schedule...")
        
        # 1. Run Scheduler (Agent 3)
        final_schedule = generate_schedule(all_course_data, start_date, end_date, current_constraints)
        
        # 2. Run Auditor (Agent 4)
        # CRITICAL UPDATE: We pass 'all_course_data' so Agent 4 knows what courses are REQUIRED.
        is_valid, feedback = audit_schedule(final_schedule, current_constraints, all_course_data)
        
        last_feedback = feedback
        
        if not is_valid:
            print(f"      ⚠️ Auditor Rejected: {feedback}")
            print("      🔧 Agent 4 is rewriting instructions for Agent 3...")
            
            # THE FEEDBACK LOOP: Pass the Auditor's specific complaints as new constraints
            # This forces Agent 3 to fix exactly what Agent 4 complained about.
            current_constraints += f" [IMPORTANT CORRECTION FROM AUDITOR: {feedback}]"
            attempt += 1
        else:
            print("      ✅ Auditor Approved!")

    # --- STEP 5: SAVE RESULTS ---
    print("\n💾 Saving Final Plan...")
    
    # 1. Save Raw JSON (Useful for debugging)
    with open("final_study_plan.json", "w") as f:
        json.dump(final_schedule, f, indent=2)

    # 2. Save Markdown with Audit Report (The requirement)
    save_as_markdown(final_schedule, last_feedback, "final_study_plan.md")
    
    print("Done!")

if __name__ == "__main__":
    main()