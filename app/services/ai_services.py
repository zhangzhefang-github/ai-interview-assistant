from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import logging
import json
import re
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.prompts import (
    RESUME_ANALYSIS_PROMPT,
    JD_ANALYSIS_PROMPT,
    INTERVIEW_QUESTION_GENERATION_PROMPT,
    INTERVIEW_REPORT_GENERATION_PROMPT,
    FOLLOWUP_QUESTION_GENERATION_PROMPT,
    SYSTEM_PROMPT_FOR_JD_ANALYSIS,
    SYSTEM_PROMPT_FOR_RESUME_PARSING,
    SYSTEM_PROMPT_FOR_QUESTION_GENERATION
)
from app.core.openai_client import get_openai_client

# Import AG UI Event schemas
from app.api.v1.schemas import ag_ui_events as sse_schemas # Assuming this is the correct import path

# Define custom exception for AI JSON parsing errors
class AIJsonParsingError(Exception):
    """Custom exception for errors during AI response JSON parsing."""
    def __init__(self, message, raw_output=None, attempted_json=None, parsing_exception=None):
        super().__init__(message)
        self.raw_output = raw_output
        self.attempted_json = attempted_json
        self.parsing_exception = parsing_exception

logger = logging.getLogger(__name__)

async def parse_resume(resume_text: str) -> str:
    """
    Parses the resume text using an LLM to extract structured information.

    Args:
        resume_text: The raw text of the candidate's resume.

    Returns:
        A string containing the structured information extracted by the LLM.
    """
    logger.info(f"Starting resume parsing. Resume text length: {len(resume_text)}")
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini",  # Changed model to match call_llm.py
        openai_api_base=settings.OPENAI_API_BASE, # Added openai_api_base
        request_timeout=60 # Added request_timeout
    )
    
    prompt_template = ChatPromptTemplate.from_template(RESUME_ANALYSIS_PROMPT)
    
    # Using LCEL (LangChain Expression Language) to construct the chain
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        logger.debug("Sending resume to LLM for parsing")
        structured_resume_info = await chain.ainvoke({"resume_text": resume_text})
        logger.info(f"Successfully parsed resume. Structured info length: {len(structured_resume_info)}")
        return structured_resume_info
    except (APITimeoutError, APIConnectionError) as e: # More specific error handling
        logger.error(f"Timeout or connection error parsing resume: {e}", exc_info=True)
        return "Error: AI service timeout or connection issue during resume parsing."
    except Exception as e:
        logger.error(f"Error parsing resume: {e}", exc_info=True)
        return "Error: Could not parse resume."

async def analyze_jd(jd_text: str) -> str:
    """
    Analyzes the job description text using an LLM to extract key requirements.

    Args:
        jd_text: The raw text of the job description.

    Returns:
        A string containing the key requirements extracted by the LLM.
    """
    logger.info(f"Starting JD analysis. JD text length: {len(jd_text)}")
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini",
        openai_api_base=settings.OPENAI_API_BASE,
        request_timeout=60 # Added request_timeout
    )
    
    prompt_template = ChatPromptTemplate.from_template(JD_ANALYSIS_PROMPT)
    
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        logger.debug("Sending JD to LLM for analysis")
        analyzed_jd_info = await chain.ainvoke({"jd_text": jd_text})
        logger.info(f"Successfully analyzed JD. Analyzed info length: {len(analyzed_jd_info)}")
        return analyzed_jd_info
    except (APITimeoutError, APIConnectionError) as e: # More specific error handling
        logger.error(f"Timeout or connection error analyzing JD: {e}", exc_info=True)
        return "Error: AI service timeout or connection issue during JD analysis."
    except Exception as e:
        logger.error(f"Error analyzing JD: {e}", exc_info=True)
        return "Error: Could not analyze JD."

async def generate_interview_questions(
    analyzed_jd_info: str, structured_resume_info: str
) -> str:
    """
    Generates interview questions based on analyzed JD and structured resume.
    """
    logger.info(f"Starting question generation. JD info length: {len(analyzed_jd_info)}, Resume info length: {len(structured_resume_info)}")
    
    try:
        logger.debug(f"Sending prompt to OpenAI for question generation")
        response = await get_openai_client().chat.completions.create(
            model=settings.OPENAI_MODEL_NAME_QUESTION_GENERATION,
            messages=[{
                "role": "user", 
                "content": INTERVIEW_QUESTION_GENERATION_PROMPT.format(
                    analyzed_jd=analyzed_jd_info,
                    structured_resume=structured_resume_info
                )
            }],
            temperature=settings.OPENAI_TEMPERATURE_QUESTION_GENERATION,
            max_tokens=512,
            timeout=60.0 # Explicitly set timeout here too
        )
        generated_questions_text = response.choices[0].message.content.strip()
        logger.info(f"Question generation completed. Output length: {len(generated_questions_text)}")
        return generated_questions_text
    except (APITimeoutError, APIConnectionError) as e:
        logger.error(f"Timeout or connection error during question generation: {e}", exc_info=True)
        raise AIJsonParsingError(message=f"AI service timeout or connection issue during question generation: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error during question generation: {e}")
        raise

async def generate_interview_report(
    analyzed_jd_info: str, 
    structured_resume_info: str, 
    conversation_log: str
) -> str:
    """
    Generates an interview report based on JD, resume, and conversation log.

    Args:
        analyzed_jd_info: The string output from analyze_jd.
        structured_resume_info: The string output from parse_resume.
        conversation_log: The text of the interview conversation.

    Returns:
        A string containing the generated interview report.
    """
    logger.info(f"Starting interview report generation. JD info length: {len(analyzed_jd_info)}, Resume info length: {len(structured_resume_info)}, Conversation log length: {len(conversation_log)}")
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini", # Using gpt-4o-mini for potentially better summarization
        openai_api_base=settings.OPENAI_API_BASE,
        request_timeout=60 # Added request_timeout
    )
    prompt_template = ChatPromptTemplate.from_template(INTERVIEW_REPORT_GENERATION_PROMPT)
    chain = prompt_template | llm | StrOutputParser()
    try:
        logger.debug("Sending data to LLM for interview report generation")
        report_text = await chain.ainvoke({
            "analyzed_jd": analyzed_jd_info,
            "structured_resume": structured_resume_info,
            "conversation_log": conversation_log
        })
        logger.info(f"Successfully generated interview report. Report length: {len(report_text)}. Preview: '{(report_text[:100] + '...') if report_text and len(report_text) > 100 else report_text}'")
        return report_text
    except (APITimeoutError, APIConnectionError) as e: # More specific error handling
        logger.error(f"Timeout or connection error generating interview report: {e}", exc_info=True)
        return "Error: AI service timeout or connection issue during report generation."
    except Exception as e:
        logger.error(f"Error generating interview report: {e}", exc_info=True)
        return "Error: Could not generate interview report."

async def generate_followup_questions_service(
    original_question: str, # Renamed from last_question to match caller
    candidate_answer: str,
    task_id: str,            # Added
    logger_instance: logging.Logger, # Added
    analyzed_jd_info: str = "", 
    structured_resume_info: str = ""
): # Return type is now an async generator, so no -> str
    """
    Generates followup questions as an async stream of SSE-formatted events.
    """
    logger_instance.info(f"Task {task_id}: Starting followup question generation stream. Original Q: '{original_question[:50]}...', Answer: '{candidate_answer[:50]}...'")
    logger_instance.debug(f"Task {task_id}: JD info length (for followup): {len(analyzed_jd_info)}, Resume info length (for followup): {len(structured_resume_info)}")

    try:
        # Yield a thought event indicating the process is starting
        yield {
            "event": sse_schemas.AgUiEventType.THOUGHT.value,
            "data": json.dumps(sse_schemas.AgUiThoughtData(task_id=task_id, thought="正在根据最新交互生成追问问题...").model_dump())
        }

        logger_instance.debug(f"Task {task_id}: Sending prompt to OpenAI for followup question generation")
        response = await get_openai_client().chat.completions.create(
            model=settings.OPENAI_MODEL_NAME_QUESTION_GENERATION, 
            messages=[{
                "role": "user", 
                "content": FOLLOWUP_QUESTION_GENERATION_PROMPT.format(
                    analyzed_jd=analyzed_jd_info if analyzed_jd_info else "N/A", # Ensure format keys match prompt
                    structured_resume=structured_resume_info if structured_resume_info else "N/A", # Ensure format keys match prompt
                    last_question=original_question, # Assuming prompt uses last_question
                    candidate_answer=candidate_answer
                )
            }],
            temperature=settings.OPENAI_TEMPERATURE_QUESTION_GENERATION, 
            max_tokens=300,
            timeout=60.0
        )
        generated_followups_text = response.choices[0].message.content.strip()
        logger_instance.info(f"Task {task_id}: Followup question raw LLM output received (length: {len(generated_followups_text)}). Output: '{generated_followups_text[:100]}...'")

        # --- Improved Parsing Logic for Followup Questions ---
        followup_questions = []
        # By default, assume the raw text is what we might need to parse line-by-line in fallback
        text_for_fallback_parsing = generated_followups_text
        
        json_str_to_parse = None

        # 1. Try to extract JSON from markdown code block
        # Regex to find ```json (...) ``` and capture the content inside
        # Corrected Regex:
        markdown_match = re.search(r"```json\s*([\s\S]+?)\s*```", generated_followups_text, re.DOTALL)
        
        if markdown_match:
            json_str_to_parse = markdown_match.group(1).strip()
            logger_instance.info(f"Task {task_id}: Extracted JSON from markdown: '{json_str_to_parse[:100]}...'")
        else:
            # 2. If no markdown, try to use the stripped raw text directly if it looks like JSON
            stripped_text = generated_followups_text.strip()
            if (stripped_text.startswith("{") and stripped_text.endswith("}")) or \
               (stripped_text.startswith("[") and stripped_text.endswith("]")):
                json_str_to_parse = stripped_text
                logger_instance.info(f"Task {task_id}: Using stripped raw text as potential JSON: '{json_str_to_parse[:100]}...'")

        if json_str_to_parse:
            try:
                parsed_data = json.loads(json_str_to_parse)
                if isinstance(parsed_data, dict) and "followup_questions" in parsed_data and isinstance(parsed_data["followup_questions"], list):
                    followup_questions = [str(q).strip() for q in parsed_data["followup_questions"] if str(q).strip()]
                    logger_instance.info(f"Task {task_id}: Parsed {len(followup_questions)} followup questions from dict's 'followup_questions' key.")
                elif isinstance(parsed_data, list):
                    followup_questions = [str(q).strip() for q in parsed_data if str(q).strip()]
                    logger_instance.info(f"Task {task_id}: Parsed {len(followup_questions)} followup questions from direct JSON list.")
                else:
                    logger_instance.warning(f"Task {task_id}: Parsed JSON from '{json_str_to_parse[:100]}...' is not a recognized list or dict structure. Will attempt fallback line parsing on original text.")
                    # No followup_questions extracted here, so fallback will be triggered if this path is taken
            except json.JSONDecodeError as e:
                logger_instance.warning(f"Task {task_id}: JSON parsing failed for extracted/direct string '{json_str_to_parse[:100]}...'. Reason: {e}. Will attempt fallback line parsing on original text.")
                # Fallback will be triggered as followup_questions is still empty

        # 3. Fallback to line splitting if JSON parsing failed or didn't yield questions
        if not followup_questions:
            logger_instance.info(f"Task {task_id}: Entering fallback parsing for: '{text_for_fallback_parsing[:100]}...'")
            potential_questions = text_for_fallback_parsing.split('\\n')
            temp_questions = []
            for line in potential_questions:
                # More aggressive skipping of common JSON/markdown structural lines
                # and lines that are too short to be meaningful questions after stripping.
                line_strip = line.strip()
                if line_strip.startswith("```") or \
                   line_strip.startswith("{") or line_strip.startswith("}") or \
                   line_strip.startswith("[") or line_strip.startswith("]") or \
                   line_strip.lower().startswith('"followup_questions":') or \
                   line_strip.lower() == '"followup_questions": [' or \
                   len(line_strip) < 3: # Heuristic: very short lines are unlikely questions
                    continue
                
                # Remove typical list item prefixes (numbers, bullets)
                cleaned_line = re.sub(r"^\\s*([\\d\\.\\-\\*>]+\\s*)+", "", line_strip).strip()
                
                # Remove surrounding quotes if they are likely from JSON string representation within a larger text
                if cleaned_line.startswith('"') and cleaned_line.endswith('"'):
                    cleaned_line = cleaned_line[1:-1].strip()
                # Remove trailing comma if it's likely from JSON array item
                if cleaned_line.endswith(','):
                    cleaned_line = cleaned_line[:-1].strip()
                
                if cleaned_line: # Add if not empty after cleaning
                    temp_questions.append(cleaned_line)
            
            followup_questions = temp_questions
            logger_instance.info(f"Task {task_id}: Fallback line splitting yielded {len(followup_questions)} potential questions.")
        # --- End of Improved Parsing Logic ---

        if not followup_questions:
            logger_instance.info(f"Task {task_id}: No followup questions were generated or parsed successfully.")
            yield {
                "event": sse_schemas.AgUiEventType.THOUGHT.value,
                "data": json.dumps(sse_schemas.AgUiThoughtData(task_id=task_id, thought="No actionable followup questions generated.").model_dump())
            }
        else:
            for i, q_text in enumerate(followup_questions):
                # Yield question_chunk (optional, for more granular streaming, here same as generated)
                # For simplicity, let's assume each question is a single chunk for now
                yield {
                    "event": sse_schemas.AgUiEventType.QUESTION_CHUNK.value,
                    "data": json.dumps(sse_schemas.AgUiQuestionChunkData(task_id=task_id, chunk_text=q_text, is_partial=False).model_dump())
                }
                # Yield question_generated
                yield {
                    "event": sse_schemas.AgUiEventType.QUESTION_GENERATED.value,
                    "data": json.dumps(sse_schemas.AgUiQuestionGeneratedData(
                        task_id=task_id,
                        question_text=q_text,
                        question_order=i + 1,
                        total_questions=len(followup_questions)
                    ).model_dump())
                }
                logger_instance.info(f"Task {task_id}: Yielded followup question {i+1}: {q_text[:50]}...")
        
        logger_instance.info(f"Task {task_id}: Followup question generation stream completed within service.")

    except (APITimeoutError, APIConnectionError) as e:
        logger_instance.error(f"Task {task_id}: Timeout or connection error during followup question generation: {e}", exc_info=True)
        yield {
            "event": sse_schemas.AgUiEventType.ERROR.value,
            "data": json.dumps(sse_schemas.AgUiErrorData(task_id=task_id, error_message=f"AI service timeout or connection issue: {str(e)}").model_dump())
        }
    except AIJsonParsingError as e: # Catch if LLM call itself raises this for some reason (e.g. invalid API key response)
        logger_instance.error(f"Task {task_id}: AIJsonParsingError during followup: {e.message}", exc_info=True)
        yield {
            "event": sse_schemas.AgUiEventType.ERROR.value,
            "data": json.dumps(sse_schemas.AgUiErrorData(task_id=task_id, error_message=e.message, raw_ai_output=e.raw_output).model_dump())
        }
    except Exception as e:
        logger_instance.error(f"Task {task_id}: Unexpected error during followup question generation stream: {e}", exc_info=True)
        yield {
            "event": sse_schemas.AgUiEventType.ERROR.value,
            "data": json.dumps(sse_schemas.AgUiErrorData(task_id=task_id, error_message=f"Unexpected server error in followup generation: {str(e)}").model_dump())
        }
    finally:
        logger_instance.info(f"Task {task_id}: generate_followup_questions_service finished.")

# Example usage (for local testing, can be removed or commented out later)
async def main_test():
    # Test parse_resume
    sample_resume_text = """
    张三
    电话: 13800138000
    邮箱: zhangsan@example.com

    教育背景：
    2015-2019 北京大学 计算机科学与技术 学士

    工作经历：
    2019-2023 谷歌软件工程师
    - 负责开发XX系统
    - 优化了YY模块性能30%

    技能：
    Python, Java, C++, 机器学习

    个人亮点：
    快速学习能力强，团队合作优秀。
    """
    print("Parsing sample resume...")
    parsed_resume_result = await parse_resume(sample_resume_text)
    print("\n--- Parsed Resume Info ---")
    print(parsed_resume_result)
    print("\n" + "="*50 + "\n")

    # Test analyze_jd
    sample_jd_text = """
    职位名称：高级后端工程师 (Python)

    工作职责：
    1. 负责核心业务系统的设计、开发和维护；
    2. 参与技术方案设计和评审，解决复杂技术问题；
    3. 持续优化系统性能、稳定性和可扩展性；
    4. 编写高质量的技术文档。

    任职要求：
    1. 计算机相关专业本科及以上学历，3年以上Python后端开发经验；
    2. 精通Python语言，熟悉Flask/Django等主流Web框架；
    3. 熟悉MySQL、Redis、MongoDB等常用数据库和缓存技术；
    4. 熟悉Linux操作系统和Shell脚本编程；
    5. 熟悉Docker等容器化技术，有微服务架构经验者优先；
    6. 具备良好的编码习惯和技术文档编写能力；
    7. 具备良好的沟通能力和团队协作精神，有较强的责任心和抗压能力。
    """
    print("Analyzing sample JD...")
    analyzed_jd_result = await analyze_jd(sample_jd_text)
    print("\n--- Analyzed JD Info ---")
    print(analyzed_jd_result)
    print("\n" + "="*50 + "\n")

    # Test generate_interview_questions
    generated_questions_result = "Error: Could not generate interview questions." # Default value
    if not parsed_resume_result.startswith("Error:") and not analyzed_jd_result.startswith("Error:"):
        print("Generating interview questions...")
        generated_questions_result = await generate_interview_questions(
            analyzed_jd_info=analyzed_jd_result, 
            structured_resume_info=parsed_resume_result
        )
        print("\n--- Generated Interview Questions ---")
        print(generated_questions_result)
    else:
        print("Skipping question generation due to previous errors.")
    print("\n" + "="*50 + "\n")

    # Test generate_interview_report
    sample_conversation_log = """
    面试官：请您详细描述在谷歌工作期间，您参与的一个核心业务系统的设计与开发过程，具体您在其中担当了什么角色，遇到了哪些技术挑战，您是如何解决这些问题的？
    张三：在谷歌期间，我作为核心开发人员参与了"智慧城市交通调度系统"的设计与开发。我主要负责后端数据处理和算法模块。遇到的主要挑战是高并发请求下的实时数据一致性保证，我们采用了分布式锁和最终一致性方案，并结合Kafka消息队列异步处理非核心逻辑，成功解决了这个问题。

    面试官：您提到优化了YY模块性能30%，请问您具体采取了哪些措施？在这个过程中，您是如何评估和监控系统性能的？
    张三：针对YY模块，我首先通过性能分析工具定位到瓶颈主要在数据库查询和部分计算逻辑。然后，我对关键SQL进行了优化，增加了缓存层（Redis），并将部分频繁计算的结果预计算。性能评估主要通过JMeter进行压力测试，并结合Prometheus和Grafana监控关键指标如QPS、响应时间和CPU/内存使用率。

    面试官：在您过往的开发经验中，您使用过哪些数据库技术（如MySQL、Redis、MongoDB）？能否分享一个实例，说明您如何进行数据库的选择和优化？
    张三：我熟悉MySQL、Redis和MongoDB。在一个电商项目中，对于商品信息这种结构化数据且需要事务保证的场景，我们选择了MySQL。对于用户会话、购物车这类读写频繁且对一致性要求不极致的场景，我们用了Redis作为缓存和快速存储。对于评论、日志这类非结构化数据，则考虑使用MongoDB。数据库优化方面，除了SQL优化，还会关注索引设计、分库分表策略等。
    """
    if not parsed_resume_result.startswith("Error:") and not analyzed_jd_result.startswith("Error:"):
        print("Generating interview report...")
        generated_report_result = await generate_interview_report(
            analyzed_jd_info=analyzed_jd_result,
            structured_resume_info=parsed_resume_result,
            conversation_log=sample_conversation_log
        )
        print("\n--- Generated Interview Report ---")
        print(generated_report_result)
    else:
        print("Skipping report generation due to previous errors.")

    # Test followup question generation
    print("\n" + "="*50 + "\n")
    print("Testing followup question generation...")
    sample_last_question = "您提到优化了YY模块性能30%，请问您具体采取了哪些措施？在这个过程中，您是如何评估和监控系统性能的？"
    sample_candidate_answer = "针对YY模块，我首先通过性能分析工具定位到瓶颈主要在数据库查询和部分计算逻辑。然后，我对关键SQL进行了优化，增加了缓存层（Redis），并将部分频繁计算的结果预计算。性能评估主要通过JMeter进行压力测试，并结合Prometheus和Grafana监控关键指标如QPS、响应时间和CPU/内存使用率。"
    
    if not analyzed_jd_result.startswith("Error:") and not parsed_resume_result.startswith("Error:"):
        try:
            followup_questions_result = await generate_followup_questions_service(
                original_question=sample_last_question,
                candidate_answer=sample_candidate_answer,
                task_id="sample_task_id",
                logger_instance=logger,
                analyzed_jd_info=analyzed_jd_result,
                structured_resume_info=parsed_resume_result
            )
            print("\n--- Generated Followup Questions ---")
            for event in followup_questions_result:
                print(event["event"], event["data"])
        except Exception as e:
            print(f"Error during followup question generation test: {e}")
    else:
        print("Skipping followup question generation test due to previous errors in JD/Resume analysis.")

if __name__ == "__main__":
    import asyncio
    # To run this test: python -m app.services.ai_services
    # Ensure your OPENAI_API_KEY is set in a .env file in the project root.
    asyncio.run(main_test()) 