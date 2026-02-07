import os
import json
import datetime
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

# --- IMPORT AGENT SKILLS ---
from agent1_sorter import sort_files, extract_header_text
from agent2_ranking import analyze_course
from agent3_scheduler import generate_schedule
from agent4_confirming import audit_schedule

# --- CONFIGURATION ---
UPLOAD_DIR = "uploaded_files"
OUTPUT_FILE = "final_study_plan.md"
MAX_RETRIES = 3

@dataclass
class PlannerState:
    """Represents the shared memory/state of the Agent Team."""
    user_hints: str = None
    user_constraints: str = "None"
    start_date: str = None
    end_date: str = None
    course_files: Dict = field(default_factory=dict)
    course_analysis: List[Dict] = field(default_factory=list)
    draft_schedule: Dict = field(default_factory=dict)
    feedback_history: List[str] = field(default_factory=list)

class StudyAgentTeam:
    def __init__(self):
        self.state = PlannerState()
        self.setup_environment()

    def setup_environment(self):
        print("\n===========================================")
        print("   🎓  FINAL.AI - INTELLIGENT AGENT TEAM   ")
        print("===========================================\n")
        
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            print(f"📂 Created '{UPLOAD_DIR}'. Please add PDFs and restart.")
            exit()
        
        self.pdf_files = [
            os.path.join(UPLOAD_DIR, f) 
            for f in os.listdir(UPLOAD_DIR) 
            if f.endswith('.pdf')
        ]
        
        if not self.pdf_files:
            print(f"⚠️  No PDFs found in '{UPLOAD_DIR}'!")
            exit()

    def get_user_context(self):
        """Step 0: Human-in-the-Loop Input"""
        print("--- 🤖 AGENT CONFIGURATION ---")
        hints = input("1. User Hints (e.g. 'MATH 136' or enter to skip): ")
        self.state.user_hints = hints.strip() if hints.strip() else None

        constraints = input("2. Personal Constraints (e.g. 'Wake up 11am', 'No Fridays'): ")
        if constraints.strip():
            self.state.user_constraints = constraints

        default_end = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
        end_input = input(f"3. Target End Date (YYYY-MM-DD) [Default: {default_end}]: ")
        self.state.end_date = end_input.strip() if end_input.strip() else default_end
        self.state.start_date = datetime.date.today().strftime("%Y-%m-%d")

    def run_agent_1_sorter(self):
        """Agent 1: The Librarian"""
        print("\n🚀 AGENT 1 (Sorter): Organizing knowledge base...")
        sorted_files = sort_files(self.pdf_files, self.state.user_hints)
        
        if not sorted_files:
            print("❌ Agent 1 failed to identify courses.")
            exit()
            
        self.state.course_files = sorted_files
        print(f"   -> Identified {len(sorted_files)} categories.")

    def run_agent_2_analyst(self):
        """Agent 2: The Analyst"""
        print("\n🧠 AGENT 2 (Analyst): Estimating workload & difficulty...")
        
        # Context string for relative difficulty scaling
        course_list_str = ", ".join([c for c in self.state.course_files.keys() if c != "General_Items"])
        
        for course_name, file_paths in self.state.course_files.items():
            if course_name == "General_Items": continue
            
            print(f"  -> Analying: {course_name}...")
            
            # Build context from files
            structured_context = ""
            for path in file_paths:
                fname = os.path.basename(path)
                text = extract_header_text(path)
                structured_context += f"\n\n=== DOC: {fname} ===\n{text}\n=== END DOC ===\n"

            # Execute Skill
            analysis = analyze_course(
                course_name, 
                structured_context, 
                course_list_str, 
                self.state.user_constraints
            )
            
            self.state.course_analysis.append({
                "course": course_name,
                "analysis": analysis
            })

    def run_agent_loop_scheduler_auditor(self):
        """The Feedback Loop: Agent 3 (Architect) <-> Agent 4 (Auditor)"""
        print(f"\n🗓️  AGENT TEAM: Collaborative Planning ({self.state.start_date} to {self.state.end_date})...")
        
        attempt = 1
        is_valid = False
        current_constraints = self.state.user_constraints
        final_feedback = ""

        while attempt <= MAX_RETRIES and not is_valid:
            print(f"\n   🔄 Iteration {attempt}/{MAX_RETRIES}...")
            
            # --- AGENT 3: SCHEDULER ---
            print("      [Agent 3] Drafting schedule...")
            self.state.draft_schedule = generate_schedule(
                self.state.course_analysis, 
                self.state.start_date, 
                self.state.end_date, 
                current_constraints
            )

            # --- AGENT 4: AUDITOR ---
            print("      [Agent 4] Reviewing draft against requirements...")
            is_valid, feedback = audit_schedule(
                self.state.draft_schedule, 
                self.state.user_constraints, # Check against original user rules
                self.state.course_analysis   # Check against original workload requirements
            )
            
            final_feedback = feedback
            self.state.feedback_history.append(f"Attempt {attempt}: {feedback}")

            if not is_valid:
                print(f"      ⚠️  REJECTED: {feedback}")
                print("      🔧  Agent 4 is instructing Agent 3 to fix issues...")
                # Update constraints with specific correction instructions
                current_constraints += f" [CORRECTION REQUIRED: {feedback}]"
                attempt += 1
            else:
                print("      ✅ APPROVED.")

        return final_feedback

    def save_artifacts(self, audit_report):
        """Final Output Generation"""
        print("\n💾 System: Saving artifacts...")
        
        # Save JSON
        with open("final_study_plan.json", "w") as f:
            json.dump(self.state.draft_schedule, f, indent=2)
            
        # Save Markdown
        self._generate_markdown(audit_report)
        print(f"✅ Mission Complete. Plan saved to '{OUTPUT_FILE}'.")

    def _generate_markdown(self, audit_report):
        """Internal helper to render Markdown"""
        with open(OUTPUT_FILE, "w") as f:
            f.write("# 📅 Final Exam Study Plan\n\n")
            
            # Auditor Status Header
            f.write("### 🛡️ Auditor Report (Agent 4)\n")
            status_icon = "✅" if "approved" in audit_report.lower() else "⚠️"
            f.write(f"> {status_icon} **STATUS:** {audit_report}\n\n---\n")

            if not self.state.draft_schedule.get("schedule"):
                f.write("No schedule generated.")
                return

            for day_entry in self.state.draft_schedule["schedule"]:
                date = day_entry.get("date", "Unknown")
                day_name = day_entry.get("day_name", "")
                
                f.write(f"## {day_name}, {date}\n")
                f.write("| Time | Type | Task |\n| :--- | :--- | :--- |\n")
                
                for event in day_entry.get("events", []):
                    t_time = event.get("time", "")
                    t_task = event.get("task", "")
                    t_type = event.get("type", "").upper()
                    
                    icon = "📚"
                    if "BREAK" in t_type: icon = "☕"
                    elif "MEAL" in t_type: icon = "🍽️"
                    elif "PERSONAL" in t_type or "WAKE" in t_type: icon = "🛌"
                    elif "REVIEW" in t_type: icon = "🧠"
                    
                    f.write(f"| **{t_time}** | {icon} {t_type} | {t_task} |\n")
                f.write("\n---\n\n")

# --- ENTRY POINT ---
if __name__ == "__main__":
    system = StudyAgentTeam()
    system.get_user_context()
    system.run_agent_1_sorter()
    system.run_agent_2_analyst()
    final_report = system.run_agent_loop_scheduler_auditor()
    system.save_artifacts(final_report)