import os
import json

# We ONLY import Agent 1 for now
from agent1_sorter import sort_files

def main():
    print("\n===========================================")
    print("      🎓  FINAL.AI - AGENT 1 TEST  🎓")
    print("===========================================\n")
    
    # --- STEP 0: SETUP ---
    files_dir = "uploaded_files" 
    
    # Check for folder
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
        print(f"📂 Created folder '{files_dir}'.")
        print("   -> Please put your PDF files inside and run this again.")
        return

    # Find PDFs
    pdf_files = [os.path.join(files_dir, f) for f in os.listdir(files_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"⚠️  No PDFs found in '{files_dir}'! Please add some files.")
        return

    # --- STEP 1: USER INPUT (Hybrid Mode) ---
    print("--- 🤖 CONFIGURATION ---")
    print("Hit ENTER to let AI figure it out, or type course codes to help.")
    
    user_input = input("User Hints (e.g. 'MATH 136, CS 101'): ")
    # Convert empty string to None
    user_hints = user_input if user_input.strip() != "" else None

    # --- STEP 2: RUN AGENT 1 ---
    print("\n🚀 STARTING AGENT 1: Sorting Files...")
    
    # This calls your function in agent1_sorter.py
    sorted_courses = sort_files(pdf_files, user_hints)
    
    # --- STEP 3: PRINT RESULTS ---
    print("\n✅ AGENT 1 COMPLETE! Here is what we found:\n")
    
    if not sorted_courses:
        print("❌ No courses identified. (Did you add files?)")
    else:
        # Pretty print the dictionary so you can check the logic
        print(json.dumps(sorted_courses, indent=4))

if __name__ == "__main__":
    main()