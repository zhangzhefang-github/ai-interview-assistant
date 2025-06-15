
# RESUME_ANALYSIS_PROMPT = """
# 你是一位经验丰富的HR专家，请帮助解析以下候选人简历，并输出以下结构化信息：
# 1. 姓名
# 2. 联系方式（电话、邮箱）
# 3. 教育背景（学历、院校、专业、起止时间）
# 4. 工作经历（公司、职位、起止时间、工作内容）
# 5. 技能关键词
# 6. 个人亮点总结

# 简历内容如下：
# {resume_text}

# 请严格按照上述格式输出，不要加入多余文字。
# """
RESUME_ANALYSIS_PROMPT = """
你是一位经验丰富的HR专家，请帮助从以下候选人简历中提取结构化关键信息，并输出标准化结果。请完整识别并分类信息，确保提取重要的项目和技术细节，输出内容如下：

1. 姓名
2. 联系方式（电话、邮箱）
3. 教育背景（学历、学校、专业、起止时间，如信息缺失请标明“缺失”）
4. 工作经历（每段包含：公司、职位、起止时间、主要职责）
5. 项目经历（如有多项请分条列出，每项包含以下要素）：
   - 项目名称
   - 所属公司或组织
   - 项目时间
   - 项目背景/目标
   - 候选人职责
   - 使用技术/工具/算法
   - 项目成果/业务价值
6. 技能关键词（包含但不限于：编程语言、AI算法、框架工具、大数据组件、云平台等）
7. 个人亮点总结（可包括：独立完成系统、跨团队合作、创新能力、行业理解等）
8. 其他补充信息（如开源项目、证书、论文、竞赛等）

请忠实提取，不擅自虚构。如简历中未提及，请用“缺失”表示。
简历内容如下：
{resume_text}
"""


JD_ANALYSIS_PROMPT = """
你是一名专业的招聘岗位分析专家，请根据以下岗位需求（Job Description），总结出：
1. 该岗位的核心职责
2. 关键技能要求
3. 优先考虑的附加技能
4. 理想候选人背景

岗位需求：
{jd_text}

请结构清晰、分点展示。
"""

INTERVIEW_QUESTION_GENERATION_PROMPT = """
你是一名专业的面试官，需要根据候选人的简历和岗位需求，生成专业且具有挑战性的面试问题。

**输入信息：**

*   **岗位需求分析摘要**:
    ```
    {analyzed_jd}
    ```

*   **候选人简历结构化摘要**:
    ```
    {structured_resume}
    ```

**问题生成要求**：
1. 生成5个专业且具有挑战性的面试问题
2. 问题需围绕以下维度：
   - 候选人过往经历与岗位的匹配度
   - 核心技能的实际应用能力
   - 项目经验中的具体贡献
   - 技术深度与广度
   - 解决问题的思路与方法
3. 避免过于宽泛或简单的问题
4. 确保问题具有针对性和可操作性

**输出要求**：
请严格按照以下JSON格式输出问题列表，不要添加任何其他描述性文字：
```json
{{
  "questions": [
    "问题1",
    "问题2",
    "问题3",
    "问题4",
    "问题5"
  ]
}}
```
"""

INTERVIEW_REPORT_GENERATION_PROMPT = """
你是专业的面试评估专家。请根据以下提供的职位描述（JD）分析、候选人简历摘要以及面试过程记录，为候选人生成一份全面的面试评估报告。

报告应包含以下部分：
1.  **综合评估**: 对候选人与职位匹配度的总体看法，是否推荐进入下一轮或录用，并简要说明理由。
2.  **能力维度分析**: 详细评估候选人在以下几个关键维度的表现（请结合JD要求和面试记录）。针对每个维度，请给出1-5分的整数评分，其中：
    *   1分：远未达到期望，存在严重问题。
    *   2分：部分达到期望，有较多不足，需重点改进。
    *   3分：基本达到期望，表现合格。
    *   4分：良好，超出期望，表现不错。
    *   5分：优秀，远超期望，表现突出。
    请务必基于JD要求和面试中的具体行为事例进行客观、审慎的评分。
    评估维度如下：
    *   专业技能与知识（与JD的相关性、深度、广度）
    *   解决问题的能力（分析问题的逻辑性、方法、创新性）
    *   沟通表达能力（清晰度、逻辑性、倾听与理解、非语言表达）
    *   团队协作倾向（通过过往经历和面试问答体现）
    *   学习能力与潜力（对新知识的接受度、过往学习成就）
    *   其他与JD特别相关的能力（例如领导力、项目管理能力等，请自行判断）
    请对每个维度提供具体的行为事例作为支撑。
3.  **亮点与优势**: 总结候选人的主要优点和突出表现。
4.  **风险与待发展点**: 指出候选人可能存在的风险、不足或与职位要求尚有差距的地方，并尽可能提供具体建议。
5.  **建议提问（如果进入下一轮）**:（可选）如果推荐进入下一轮，可以提出1-2个建议在后续面试中进一步考察的问题。

**输入信息：**

*   **职位描述（JD）分析摘要**:
    ```
    {analyzed_jd}
    ```

*   **候选人简历结构化摘要**:
    ```
    {structured_resume}
    ```

*   **面试过程记录**:
    ```
    {conversation_log}
    ```

**输出要求**：
请严格按照以上报告结构进行组织。确保内容客观、具体、专业。
请用中文撰写这份评估报告。
在报告的最后，请务必严格按照以下格式输出JSON块，其中每个能力维度的评分应为1-5的整数。不要在该JSON块前后添加任何其他描述性文字或标题：
```json
{{
  "CANDIDATE_CAPABILITY_ASSESSMENT_JSON": {{
    "专业技能与知识": 3,
    "解决问题的能力": 4,
    "沟通表达能力": 3,
    "团队协作倾向": 4,
    "学习能力与潜力": 5
  }}
}}
```

"""

# You can add more prompts here for other AI functionalities
# e.g., a prompt for summarizing a long interview transcript, etc.

COMMON_FOLLOW_UP_QUESTIONS = [
    "能否详细说明一下您在其中扮演的具体角色？",
    "在这个过程中，您遇到的最大挑战是什么？您是如何克服的？",
    "这个项目/经验给您带来的最主要的收获是什么？",
    "如果可以重新来一次，您会在哪些方面做得不同？为什么？",
    "您是如何量化您提到的这个成果的？有哪些具体数据支撑吗？",
    "针对您提到的[某一点]，能再展开讲讲吗？"
] 

FOLLOWUP_QUESTION_GENERATION_PROMPT = """
你是一位资深的面试官，需要根据面试官提出的上一个问题、候选人的回答，并结合整体的岗位需求和候选人背景，生成3-4个有深度、有针对性的追问建议。

**输入信息：**

*   **岗位需求分析摘要 (可选，但强烈建议提供以确保相关性)**:
    ```
    {analyzed_jd}
    ```

*   **候选人简历结构化摘要 (可选，但强烈建议提供以确保相关性)**:
    ```
    {structured_resume}
    ```

*   **面试官的上一个问题**:
    ```
    {last_question}
    ```

*   **候选人对该问题的回答**:
    ```
    {candidate_answer}
    ```

**追问建议生成要求**：
1.  生成3-4个追问问题。
2.  追问应紧密围绕候选人回答中的关键信息、模糊点、亮点或潜在的深挖点。
3.  追问应能进一步考察候选人的真实能力、思考深度或经验细节。
4.  避免与已提出的问题过于重复，或提出与当前对话上下文无关的问题。
5.  如果候选人的回答很简单或信息量不足，可以生成一些帮助其展开或提供更多细节的问题。
6.  确保问题专业且有礼貌。

**输出要求**：
请严格按照以下JSON格式输出问题列表，不要添加任何其他描述性文字：
```json
{{
  "followup_questions": [
    "追问建议1",
    "追问建议2",
    "追问建议3"
  ]
}}
```
""" 

# System prompts for more granular control if needed
SYSTEM_PROMPT_FOR_JD_ANALYSIS = """
You are an AI assistant helping to analyze job descriptions. 
Focus on extracting key responsibilities, skills, and qualifications.
Present the output in a structured and concise manner.
"""

SYSTEM_PROMPT_FOR_RESUME_PARSING = """
You are an AI assistant helping to parse resumes.
Extract information such as contact details, education, work experience, skills, and projects.
Structure the output clearly, ideally in a JSON-like format if complex, or a well-organized text format.
"""

SYSTEM_PROMPT_FOR_QUESTION_GENERATION = """
You are an AI assistant specialized in generating insightful interview questions.
Given the analyzed job description and structured resume, generate relevant questions.
Ensure questions cover various aspects like technical skills, behavioral traits, and experience.
Output the questions in a JSON format: {"questions": ["question1", "question2", ...]}
""" 