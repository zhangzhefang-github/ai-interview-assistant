# app/services/ai_report_generator.py

import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
# from dotenv import load_dotenv # Potentially use dotenv for local development API key management

# For local development, you might use:
# load_dotenv() 
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#     raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it.")

# In a production or containerized environment, API keys are typically set directly as environment variables.
# For simplicity in this shared context, we'll assume OPENAI_API_KEY is available in the environment
# where the FastAPI app runs. The actual key needs to be configured by the user.

# Placeholder for a logger if you have a centralized one, or use standard logging
import logging
logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """
You are a Senior HR Specialist and Technical Interviewer. Based on the provided interview dialogue, job description, and candidate resume, please generate a professional interview assessment report.

**1. Job Description (JD):**
{job_description}

**2. Candidate Resume Summary:**
{candidate_resume}

**3. Interview Dialogue Records:**
---
{interview_dialogues}
---

**Please structure your report with the following sections:**

**I. Summary of Candidate's Key Responses:**
   - Briefly summarize the candidate's main points and information provided for key questions.

**II. Preliminary Skills and Experience Assessment (against JD):**
   - Based on the dialogue, assess the candidate's alignment with the skills and experience required in the JD.
   - Highlight matching aspects and potential gaps.

**III. Communication and Presentation Skills (Initial Impression):**
   - Briefly comment on the candidate's communication style, clarity, and overall presentation during the interview.

**IV. Overall Preliminary Recommendation:**
   - Provide a preliminary recommendation (e.g., Proceed to next round / Hold for further consideration / Not a fit at this time).
   - Briefly state the reasons for your recommendation.

**Note:** Your report should be objective, concise, and professional. Focus on the information gathered from the interview dialogue.
"""

def generate_interview_report(
    interview_dialogues: List[str],  # List of strings, each is a full_dialogue_text for a question
    job_description: str,
    candidate_resume: str,
    llm_model_name: str = "gpt-3.5-turbo", # Configurable model name
    temperature: float = 0.3
) -> str:
    """
    Generates an interview assessment report using an LLM.

    Args:
        interview_dialogues: A list of strings, where each string is the full dialogue text
                             recorded for a specific interview question.
        job_description: The job description text.
        candidate_resume: The candidate's resume text.
        llm_model_name: The name of the LLM model to use (e.g., "gpt-3.5-turbo", "gpt-4").
        temperature: The temperature setting for the LLM.

    Returns:
        A string containing the generated interview assessment report.
        Returns an error message string if report generation fails.
    """
    if not interview_dialogues:
        logger.warning("Cannot generate report: No interview dialogues provided.")
        return "Error: No interview dialogues provided to generate the report."
    if not job_description:
        logger.warning("Cannot generate report: Job description is missing.")
        # Fallback: Generate report without JD, or return error. For MVP, let's try to proceed with a note.
        # return "Error: Job description is missing."
        job_description = "Not provided." # Or a more descriptive placeholder
    if not candidate_resume:
        logger.warning("Cannot generate report: Candidate resume is missing.")
        # Fallback: Generate report without resume, or return error.
        # return "Error: Candidate resume is missing."
        candidate_resume = "Not provided." # Or a more descriptive placeholder

    # Concatenate all dialogue segments into a single string for the prompt
    # Using a clear separator between different dialogue segments
    full_dialogue_string = "\n\n--- Next Question Dialogue ---\n\n".join(interview_dialogues)

    try:
        # Ensure OPENAI_API_KEY is set in the environment where this code runs
        # If not using LangChain's auto-detection, you might need to pass it explicitly:
        # llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name=llm_model_name, temperature=temperature)
        llm = ChatOpenAI(model_name=llm_model_name, temperature=temperature)
        
        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        
        # LLMChain is a simple way to combine a prompt and an LLM.
        # For more complex logic (e.g., multiple LLM calls, tool usage), Agent or LCEL would be used.
        chain = LLMChain(llm=llm, prompt=prompt)
        
        logger.info(f"Generating report for interview. Dialogues length: {len(full_dialogue_string)}, JD length: {len(job_description)}, Resume length: {len(candidate_resume)}")

        # Invoke the chain with the required input variables
        response = chain.invoke({
            "job_description": job_description,
            "candidate_resume": candidate_resume,
            "interview_dialogues": full_dialogue_string
        })
        
        generated_report = response.get("text", "") #.text for LLMChain, .content for ChatMessage
        if not generated_report.strip():
            logger.error("LLM generated an empty report.")
            return "Error: AI service generated an empty report."

        logger.info("Successfully generated interview report.")
        return generated_report

    except Exception as e:
        # Catching a broad exception for now. In production, you'd want more specific error handling
        # (e.g., openai.APIError, openai.RateLimitError, openai.AuthenticationError)
        # LangChain might also wrap these errors.
        logger.error(f"Error generating interview report: {e}", exc_info=True)
        return f"Error: Failed to generate AI report due to an internal error ({type(e).__name__}). Please try again later."

# Example Usage (for testing this service directly, not part of the FastAPI app)
if __name__ == "__main__":
    # This example assumes OPENAI_API_KEY is set in your environment
    # You would need to mock or provide actual data for testing
    print("Testing AI Report Generator Service...")
    sample_dialogues = [
        "Candidate's response to 'Tell me about yourself': I am a software engineer with 5 years of experience...",
        "Candidate's response to 'Describe a challenging project': I once worked on a project with a tight deadline..."
    ]
    sample_jd = "Seeking a Senior Software Engineer proficient in Python, FastAPI, and SQL. Strong problem-solving skills required."
    sample_resume = "John Doe - Software Engineer. Skills: Python, Java, SQL. Experience: 5 years at XYZ Corp."

    # Ensure your OPENAI_API_KEY is set in your environment for this direct test to work
    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping direct test: OPENAI_API_KEY is not set.")
    else:
        print(f"OPENAI_API_KEY found, proceeding with test call to {os.getenv('OPENAI_API_BASE', 'OpenAI API default')}")
        report = generate_interview_report(sample_dialogues, sample_jd, sample_resume)
        print("\n--- Generated Report ---")
        print(report)
        print("--- End of Report ---") 