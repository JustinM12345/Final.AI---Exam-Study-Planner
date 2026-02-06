import os
import json
import time

# --- IMPORTS ---
from agent1_sorter import sort_files, extract_header_text
from agent2_ranking import analyze_course

def main():
    print("\n===========================================")
    print("   🎓  FINAL.AI - AGENTS 1 & 2 RUN  🎓")
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
    user_input = input("User Hints (optional, e.g. 'MATH 136'): ")
    user_hints = user_input if user_input.strip() != "" else None

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

    # [NEW] Create a list of all courses so Agent 2 knows the full workload
    # This helps it decide that PHYS 234 is "Hard" and HLTH 204 is "Easy"
    course_list_str = ", ".join([c for c in sorted_courses.keys() if c != "General_Items"])
    
    for i, (course_name, file_paths) in enumerate(sorted_courses.items()):
        if course_name == "General_Items":
            continue 
            
        print(f"  -> Processing Course: {course_name} ({len(file_paths)} files)")
        
        # 1. Build the Structured Context (The "Bridge")
        structured_context = ""
        for path in file_paths:
            filename = os.path.basename(path)
            raw_text = extract_header_text(path)
            
            # Add headers so Agent 2 knows which file is which
            structured_context += f"\n\n=== START OF DOCUMENT: {filename} ===\n"
            structured_context += raw_text
            structured_context += f"\n=== END OF DOCUMENT: {filename} ===\n"

        # 2. Call Agent 2 with the GLOBAL CONTEXT
        # [NEW] We pass 'course_list_str' as the 3rd argument
        difficulty_data = analyze_course(course_name, structured_context, course_list_str)
        
        # 3. Store the result
        all_course_data.append({
            "course": course_name,
            "analysis": difficulty_data
        })

    # --- STEP 4: PRINT FINAL RESULTS ---
    print("\n✅ AGENT 2 COMPLETE! Here is the data for your Scheduler:\n")
    print(json.dumps(all_course_data, indent=2))

if __name__ == "__main__":
    main()