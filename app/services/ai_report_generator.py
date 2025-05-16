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

# Import the centralized prompt
from app.core.prompts import INTERVIEW_REPORT_GENERATION_PROMPT

async def generate_interview_report(
    conversation_log_str: str,  # Changed from interview_dialogues: List[str]
    job_description: str,
    candidate_resume: str,
    llm_model_name: str = "gpt-3.5-turbo", # Configurable model name
    temperature: float = 0.3
) -> str:
    """
    Generates an interview assessment report using an LLM.

    Args:
        conversation_log_str: A string containing the full, concatenated dialogue text
                              from the interview.
        job_description: The job description text.
        candidate_resume: The candidate's resume text.
        llm_model_name: The name of the LLM model to use (e.g., "gpt-3.5-turbo", "gpt-4").
        temperature: The temperature setting for the LLM.

    Returns:
        A string containing the generated interview assessment report.
        Returns an error message string if report generation fails.
    """
    if not conversation_log_str: # Check the new parameter
        logger.warning("Cannot generate report: No interview dialogue string provided.")
        return "Error: No interview dialogue string provided to generate the report."
    if not job_description:
        logger.warning("Cannot generate report: Job description is missing.")
        job_description = "Not provided."
    if not candidate_resume:
        logger.warning("Cannot generate report: Candidate resume is missing.")
        candidate_resume = "Not provided."

    # Removed the concatenation logic as conversation_log_str is now pre-formatted.
    # full_dialogue_string = "\\n\\n--- Next Question Dialogue ---\\n\\n".join(interview_dialogues)

    try:
        # Ensure OPENAI_API_KEY is set in the environment where this code runs
        # If not using LangChain\'s auto-detection, you might need to pass it explicitly:
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base = os.getenv("OPENAI_API_BASE") # Explicitly read OPENAI_API_BASE

        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            return "Error: OPENAI_API_KEY not configured."

        llm_params = {
            "model_name": llm_model_name,
            "temperature": temperature,
            "openai_api_key": openai_api_key # Explicitly pass api_key
        }
        if openai_api_base: # If OPENAI_API_BASE is set, pass it
            llm_params["openai_api_base"] = openai_api_base
            logger.info(f"Using OpenAI API Base: {openai_api_base}")
        else:
            logger.info("Using default OpenAI API Base.")
            
        llm = ChatOpenAI(**llm_params)
        
        # Use the imported prompt
        prompt = ChatPromptTemplate.from_template(INTERVIEW_REPORT_GENERATION_PROMPT)
        
        # LLMChain is a simple way to combine a prompt and an LLM.
        # For more complex logic (e.g., multiple LLM calls, tool usage), Agent or LCEL would be used.
        chain = LLMChain(llm=llm, prompt=prompt)
        
        logger.info(f"Generating report for interview. Dialogues length: {{len(conversation_log_str)}}, JD length: {{len(job_description)}}, Resume length: {{len(candidate_resume)}}")

        # Invoke the chain with the required input variables that match the prompt template
        response = await chain.ainvoke({
            "analyzed_jd": job_description,
            "structured_resume": candidate_resume,
            "conversation_log": conversation_log_str # Use the new parameter directly
        })
        
        generated_report = response.get("text", "")
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
    # Update example usage for direct testing
    sample_single_dialogue_string = """Candidate's response to 'Tell me about yourself': I am a software engineer with 5 years of experience...

--- Next Question Dialogue ---

Candidate's response to 'Describe a challenging project': I once worked on a project with a tight deadline..."""
    sample_jd = "Seeking a Senior Software Engineer proficient in Python, FastAPI, and SQL. Strong problem-solving skills required."
    sample_resume = "John Doe - Software Engineer. Skills: Python, Java, SQL. Experience: 5 years at XYZ Corp."

    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping direct test: OPENAI_API_KEY is not set.")
    else:
        print(f"OPENAI_API_KEY found, proceeding with test call to {os.getenv('OPENAI_API_BASE', 'OpenAI API default')}")
        # To test async directly, you'd need to run it in an event loop:
        # import asyncio
        # report = asyncio.run(generate_interview_report(sample_single_dialogue_string, sample_jd, sample_resume))
        print("Async function test call needs to be run with asyncio.run(). Skipping direct execution in __main__ for now.")
        # report = generate_interview_report(sample_single_dialogue_string, sample_jd, sample_resume) 
        # print("\\n--- Generated Report ---")
        # print(report)
        # print("--- End of Report ---") 