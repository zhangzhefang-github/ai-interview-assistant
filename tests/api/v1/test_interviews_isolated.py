from fastapi import status
from fastapi.testclient import TestClient

# client fixture 会从 conftest.py 自动加载

def test_isolated_get_questions_for_non_existent_interview(client: TestClient):
    """
    在一个隔离的测试文件中，测试获取一个不存在的面试的问题。
    """
    non_existent_interview_id = 999999  # 一个几乎不可能存在的ID
    response = client.get(f"/api/v1/interviews/{non_existent_interview_id}/questions")
    
    # 期望结果：
    # 1. HTTP状态码应该是 404 Not Found
    # 2. 如果我们编辑的 `app/api/v1/endpoints/interviews.py` (只包含 get_questions_for_interview 端点)
    #    被正确加载，那么错误详情应该是 "Interview not found"。
    #    如果加载的是旧的"幽灵"版本（没有 /questions 路由），那么错误详情可能是通用的 "Not Found"。
            
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Interview not found"} 