from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.prompts import (
    RESUME_ANALYSIS_PROMPT,
    JD_ANALYSIS_PROMPT,
    INTERVIEW_QUESTION_GENERATION_PROMPT,
    INTERVIEW_REPORT_GENERATION_PROMPT
)

async def parse_resume(resume_text: str) -> str:
    """
    Parses the resume text using an LLM to extract structured information.

    Args:
        resume_text: The raw text of the candidate's resume.

    Returns:
        A string containing the structured information extracted by the LLM.
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini",  # Changed model to match call_llm.py
        openai_api_base=settings.OPENAI_API_BASE # Added openai_api_base
    )
    
    prompt_template = ChatPromptTemplate.from_template(RESUME_ANALYSIS_PROMPT)
    
    # Using LCEL (LangChain Expression Language) to construct the chain
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        structured_resume_info = await chain.ainvoke({"resume_text": resume_text})
        return structured_resume_info
    except Exception as e:
        # Basic error handling, can be improved with more specific logging/exception types
        print(f"Error parsing resume: {e}")
        # In a real app, you might want to raise a custom exception or return a specific error indicator
        return "Error: Could not parse resume."

async def analyze_jd(jd_text: str) -> str:
    """
    Analyzes the job description text using an LLM to extract key requirements.

    Args:
        jd_text: The raw text of the job description.

    Returns:
        A string containing the key requirements extracted by the LLM.
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini",
        openai_api_base=settings.OPENAI_API_BASE
    )
    
    prompt_template = ChatPromptTemplate.from_template(JD_ANALYSIS_PROMPT)
    
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        analyzed_jd_info = await chain.ainvoke({"jd_text": jd_text})
        return analyzed_jd_info
    except Exception as e:
        print(f"Error analyzing JD: {e}")
        return "Error: Could not analyze JD."

async def generate_interview_questions(analyzed_jd_info: str, structured_resume_info: str) -> str:
    """
    Generates interview questions based on analyzed JD and structured resume.

    Args:
        analyzed_jd_info: The string output from analyze_jd.
        structured_resume_info: The string output from parse_resume.

    Returns:
        A string containing the generated interview questions.
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini",
        openai_api_base=settings.OPENAI_API_BASE
    )
    prompt_template = ChatPromptTemplate.from_template(INTERVIEW_QUESTION_GENERATION_PROMPT)
    chain = prompt_template | llm | StrOutputParser()
    try:
        return await chain.ainvoke({
            "analyzed_jd": analyzed_jd_info,
            "structured_resume": structured_resume_info
        })
    except Exception as e:
        print(f"Error generating interview questions: {e}")
        return "Error: Could not generate interview questions."

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
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model_name="gpt-4o-mini", # Using gpt-4o-mini for potentially better summarization
        openai_api_base=settings.OPENAI_API_BASE
    )
    prompt_template = ChatPromptTemplate.from_template(INTERVIEW_REPORT_GENERATION_PROMPT)
    chain = prompt_template | llm | StrOutputParser()
    try:
        return await chain.ainvoke({
            "analyzed_jd": analyzed_jd_info,
            "structured_resume": structured_resume_info,
            "conversation_log": conversation_log
        })
    except Exception as e:
        print(f"Error generating interview report: {e}")
        return "Error: Could not generate interview report."

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

if __name__ == "__main__":
    import asyncio
    # To run this test: python -m app.services.ai_services
    # Ensure your OPENAI_API_KEY is set in a .env file in the project root.
    asyncio.run(main_test()) 