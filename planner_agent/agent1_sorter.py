import os
import google.generativeai as genai
import json
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Using Gemini 3.0 Flash
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview")  

# Reads the first 4 pages of the pdf (or all the pages in the pdf) in an attempt to find the course code or title
def extract_header_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(min(4, len(reader.pages))):
            text += reader.pages[i].extract_text()
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

# Prompting Gemini to search specifically for the syllabi in order to create a list of course codes and their subject
def find_syllabus_courses(file_data_list, user_hints=None):
    print("  -> Agent 1: Scanning for Syllabi to identify courses...")
    
    bulk_text = ""
    for idx, f in enumerate(file_data_list):
        bulk_text += f"--- FILE {idx}: {os.path.basename(f['path'])} ---\n"
        bulk_text += f"{f['text'][:2000]}\n\n"

    # Create a specific instruction if the user gave input
    hint_text = ""
    if user_hints:
        hint_text = f"""
        USER HINT: The user indicated they are likely taking these courses: [{user_hints}]. 
        Use this list to guide your search, but ONLY output courses if you find actual evidence (syllabi/files) for them.
        """

    # Main prompt
    prompt = f"""
    You are an Academic File Organizer.
    Scan the file headers below. 
    Identify the distinct COURSE CODES and their TOPICS.

    {hint_text}  <-- INJECT THE HINT HERE

    CRITICAL INSTRUCTION:
    1. Prioritize Syllabi/Course Outlines to find the 'source'.
    2. Extract the Course Code (e.g. CS 101, HLTH 204, PHYS 234, SYSD 300) and a short Topic Summary.
    3. If a course has multiple sections or similar names, use the topic to distinguish them.
    
    OUTPUT FORMAT:
    Return valid JSON only. Key = Course Code, Value = Short Topic Summary.
    
    EXAMPLE OUTPUT:
    {{
      "MATH 138": "Calculus II, Integrals, Series", 
      "HIST 200": "Modern History, Cold War, WWII",
      "CS 101": "Intro to Programming, Python, Loops",
      "BIOL 101": "Cell Biology, Genetics"
    }}
    
    FILES CONTENT:
    {bulk_text}
    """
    
    try:
        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"    Warning: Could not auto-detect courses ({e}). Defaulting to generic.")
        return {}


# After Gemini has identified the courses we associate the textbook and midterm material pdfs to those courses
def assign_file_to_course(filename, text, course_context_map):
    if not course_context_map:
        return "General_Items"

    # First check is to see if the filename matches
    # If the filename literally contains "HLTH 204" and that is a known course, match it immediately.
    for course_code in course_context_map.keys():
        # ignore case sensitivity
        if course_code.replace(" ", "").upper() in filename.replace(" ", "").upper():
            return course_code

    # For files that aren't titled after the course code (like the textbook) let the AI make a guess
    prompt = f"""
    Task: Match the document below to the correct Course Code.
    
    KNOWN COURSES & TOPICS:
    {json.dumps(course_context_map, indent=2)}
    
    NEW FILE TO SORT:
    Filename: {filename}
    Content Snippet: {text[:10000]}
    
    INSTRUCTIONS:
    1. ANALYZE THE TOPIC: Read the content snippet.
    2. MATCH THE TOPIC: Does "Biostatistics" match the topic of HLTH 204? (Yes).
    3. MATCH THE FILENAME: If filename is "Midterm 1", match it to the course that mentions "Midterm" in its text or simply the best topic match.
    4. BE AGGRESSIVE: Do not return "General_Items" unless the file is completely unrelated (like a cooking recipe). 
       - If it looks even slightly like Math, and you have a Math course, match it.
       - If it looks like System Dynamics (stocks/flows), match to SYSD 300.
    
    OUTPUT:
    Return ONLY the Course Code string.
    """
    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace('"', '').replace("'", "")
        
        # Ensure the AI returned a real course code from our list
        if cleaned in course_context_map:
            return cleaned
        return "General_Items"
    except Exception:
        return "General_Items"

def sort_files(file_paths, user_hints=None):
    sorted_courses = {}
    file_data = []
    
    # Step A: Read all files 
    print("Agent 1 (Sorter): Reading files...")
    for f in file_paths:
        text = extract_header_text(f)
        if text:
            file_data.append({"path": f, "text": text})
    
    # Step B: Pass the user input to finding syllabus function
    course_context_map = find_syllabus_courses(file_data, user_hints)
    print(f"  -> Identified Contexts: {course_context_map}")
    
    # Step C: Match every file (including the syllabi themselves) to the right category
    for data in file_data:
        filename = os.path.basename(data['path'])
        
        # Ask Gemini to match this specific file to the context map
        course = assign_file_to_course(filename, data['text'], course_context_map)
        
        print(f"  -> '{filename}' assigned to: {course}")
        
        # Add to the dictionary
        if course not in sorted_courses:
            sorted_courses[course] = []
        sorted_courses[course].append(data['path'])
        
    return sorted_courses