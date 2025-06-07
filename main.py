import asyncio
import time
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Warning: GOOGLE_API_KEY not found in .env file.")
else:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        print(f"Error configuring Google AI: {e}")

# --- Test Mode Flag ---
IS_TEST_MODE = False

app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- UPGRADED Helper Function to categorize guidance files ---
def load_guidance_by_type() -> dict:
    guidance_dir = "guidance"
    guidance_docs = {
        "jd": "",
        "resume": "",
        "cover_letter": ""
    }
    
    if not os.path.isdir(guidance_dir):
        print("Warning: 'guidance' directory not found.")
        return guidance_docs

    for filename in sorted(os.listdir(guidance_dir)):
        file_path = os.path.join(guidance_dir, filename)
        
        try:
            # Read text content based on file type
            text_content = ""
            if filename.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            elif filename.endswith(".pdf"):
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text_content += page.get_text()
            
            if not text_content:
                continue

            # Categorize content based on filename
            lower_filename = filename.lower()
            if "jd" in lower_filename:
                guidance_docs["jd"] += f"--- START OF GUIDANCE: {filename} ---\n{text_content}\n--- END OF GUIDANCE: {filename} ---\n\n"
            elif "resume" in lower_filename:
                guidance_docs["resume"] += f"--- START OF GUIDANCE: {filename} ---\n{text_content}\n--- END OF GUIDANCE: {filename} ---\n\n"
            elif "cover letter" in lower_filename:
                guidance_docs["cover_letter"] += f"--- START OF GUIDANCE: {filename} ---\n{text_content}\n--- END OF GUIDANCE: {filename} ---\n\n"

        except Exception as e:
            print(f"Error reading or categorizing file {filename}: {e}")

    return guidance_docs

# Helper function to correctly read uploaded files (PDF or TXT)
async def extract_text_from_upload(upload_file: UploadFile) -> str:
    """Reads an uploaded file and extracts text, handling PDF and TXT."""
    file_bytes = await upload_file.read()
    
    if upload_file.content_type == "application/pdf":
        try:
            text_content = ""
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text()
            return text_content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing PDF file {upload_file.filename}: {e}")
    elif upload_file.content_type == "text/plain":
        return file_bytes.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload_file.content_type}. Please upload PDF or TXT.")


# --- Helper function to call the AI Model ---
async def call_gemini_api(prompt: str, is_json_output: bool = True, max_retries: int = 3):
    """A reusable function to call the Gemini API and handle responses."""
    if not API_KEY and not IS_TEST_MODE:
         raise HTTPException(status_code=500, detail="Google Gemini API key is not configured on the server.")
    
    for attempt in range(max_retries):
        try:
            print(f"--- Calling Gemini API... (JSON Output: {is_json_output}) ---")
            model = genai.GenerativeModel('gemma-3-27b-it')
            response = model.generate_content(prompt)
            
            if is_json_output:
                cleaned_json_string = response.text.strip().replace("```json", "").replace("```", "")
                return json.loads(cleaned_json_string)
            else:
                return response.text
                
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = 120  # Fixed 2-minute wait for rate limits
                print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                continue
            else:
                print(f"An error occurred during a Gemini API call: {e}")
                raise HTTPException(status_code=500, detail=f"An error occurred with the AI model: {e}")

# --- The Main Orchestrator Endpoint ---
@app.post("/generate-full-application/")
async def generate_full_application(
    job_description: str = Form(...), 
    master_resume_file: UploadFile = File(...),
    story_file: UploadFile = File(...)
):
    master_resume_content = await extract_text_from_upload(master_resume_file)
    story_content = await extract_text_from_upload(story_file)
    guidance_by_type = load_guidance_by_type()

    # --- MOCK DATA FOR TEST MODE ---
    if IS_TEST_MODE:
        print("--- RUNNING IN TEST MODE ---")
        return {
            "analysis": {"keywords": ["Python", "FastAPI", "Teamwork"], "persona": "A proactive team player. Guidance was loaded."},
            "resume": "### Mocked Resume\n\nThis is the tailored resume based on the analysis.",
            "review": "### Mocked Review\n\n- **ATS Score:** 8/10\n- **Comments:** The resume looks strong.",
            "cover_letter": "### Mocked Cover Letter\n\nThis is the final cover letter."
        }

    # # --- STEP 1: Analysis (Your Prompt 1) ---
    # prompt1_analysis = f"""
    #     Readme.txt is a JD i am interested.
    #     please extract the key word according to the attached guide"_JD_Extract_Enhanced", and get some expectation from JD_Hints.txt
    #     List out all the point may relevant to this JD.
    #     Return your output as a JSON object with two keys: "keywords" (a list of strings) and "persona" (a descriptive string).

    #     GUIDE:
    #     {guidance_by_type["jd"]}

    #     JD:
    #     {job_description}
    #     """

    # --- STEP 1: Analysis (Your Prompt 1) ---
    prompt1_analysis = f"""
        Please extract keywords and the expected persona from the following Job Description, using the provided JD-specific guidelines.
        List out all the point may relevant to this Job Description.
        Return your output as a JSON object with two keys: "keywords" (a list of strings) and "persona" (a descriptive string).
        JD-SPECIFIC GUIDELINES: {guidance_by_type["jd"]}
        JOB DESCRIPTION: {job_description}
    """
    analysis_result = await call_gemini_api(prompt1_analysis, is_json_output=True)

    print("--- Waiting for 60 seconds to respect API rate limits... ---")
    time.sleep(60) # NEW: Add a delay
    
    # # --- STEP 2: Resume Generation (Your Prompt 2) ---
    # prompt2_generation = f"""
    #     Please help to polish my resume for this JD by the extracted keywords. Do not write beyond 1000 words which make it to 2 pages only. 
    #     Do not make up any information that is not stated on the resume provided.
    #     Make it ATS friendly and sound professional according to the attached guideline. Use Markdown for formatting.

    #     EXTRACTED KEYWORDS AND PERSONA:
    #     {json.dumps(analysis_result, indent=2)}
        
    #     ATTACHED GUIDELINE:
    #     {guidance_by_type["resume"]}

    #     MY MASTER RESUME:
    #     {master_resume_content}
    # """

    # --- STEP 2: Resume Generation (Now includes story context) ---
    prompt2_generation = f"""
        Please polish the master resume to be tailored for the job, based on the analysis from the previous step.
        Follow the RESUME-SPECIFIC GUIDELINES. Use the STAR stories from the story context to add more impactful and quantified achievements.
        The output should be a two page, ATS-friendly, professional resume in Markdown format. Do not invent information.

        ANALYSIS FROM PREVIOUS STEP: {json.dumps(analysis_result, indent=2)}
        RESUME-SPECIFIC GUIDELINES: {guidance_by_type["resume"]}
        MY MASTER RESUME (Primary Source): {master_resume_content}
        MY STORY CONTEXT (For impact examples): {story_content}
    """

    generated_resume = await call_gemini_api(prompt2_generation, is_json_output=False)

    print("--- Waiting for 60 seconds to respect API rate limits... ---")
    time.sleep(60) # NEW: Add a delay

    # --- STEP 2.5: Review (Your Prompt 2.5) ---
    # Note: This prompt intentionally does not include the internal guidance files,
    # as it's meant to simulate an external hiring manager's perspective.
    prompt2_5_review = f"""
        Please review the provided Job Description and the generated Resume.
        Act as a hiring manager and an ATS system in Canada.
        Provide feedback on how well the resume is tailored to the job description.
        Use Markdown for formatting your review.

        JOB DESCRIPTION:
        {job_description}

        GENERATED RESUME TO REVIEW:
        {generated_resume}
    """
    review_feedback = await call_gemini_api(prompt2_5_review, is_json_output=False)

    print("--- Waiting for 60 seconds to respect API rate limits... ---")
    time.sleep(60) # NEW: Add a delay

    # --- STEP 3: Cover Letter Generation (Your Prompt 3) ---
    prompt3_cover_letter = f"""
        Please help to draft a cover letter. Do not make up information from the provided tailored resume.
        Try to follow the hints in the COVER LETTER-SPECIFIC GUIDELINES if possible. Use Markdown for formatting.

        TAILORED RESUME (Source of truth): {generated_resume}
        COVER LETTER-SPECIFIC GUIDELINES: {guidance_by_type["cover_letter"]}
        STAR STORIES (Source for examples): {story_content}
    """
    generated_cover_letter = await call_gemini_api(prompt3_cover_letter, is_json_output=False)

    # --- FINAL STEP: Return all generated documents ---
    return {
        "analysis": analysis_result,
        "resume": generated_resume,
        "review": review_feedback,
        "cover_letter": generated_cover_letter,
    }