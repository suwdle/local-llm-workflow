from typing import Dict, Any, TypedDict
from pathlib import Path
import logging
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Type definitions
class ProjectData(TypedDict, total=False):
    project_info: str
    task_list: str
    milestones: str
    output_path: str
    error: str

# Initialize Ollama with DeepSeek-R1 model
llm = ChatOllama(
    model="deepseek-r1",
    base_url="http://localhost:11434"
)

def input_project_details(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph가 올바르게 동작하도록 입력 노드를 수정."""
    logger.info("Processing project details")
    project_info = state.get("project_info", "프로젝트 정보 없음")
    return {**state, "project_info": project_info, "output_path": "project_plan.md"}

def generate_task_list(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Generating task list")
    try:
        project_info = state["project_info"]
        task_prompt = PromptTemplate(
            input_variables=["project_info"],
            template="다음 프로젝트를 완료하기 위해 필요한 주요 작업(Task) 목록을 생성하세요.\n\n프로젝트 설명:\n{project_info}"
        )
        task_chain = LLMChain(llm=llm, prompt=task_prompt)
        task_list = task_chain.run(project_info=project_info)
        return {**state, "task_list": task_list}
    except Exception as e:
        logger.error(f"Error generating task list: {str(e)}")
        return {**state, "error": f"Failed to generate task list: {str(e)}"}

def generate_milestones(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Generating milestones")
    try:
        if "error" in state:
            return state
        task_list = state["task_list"]
        milestone_prompt = PromptTemplate(
            input_variables=["task_list"],
            template="다음 작업 목록을 기반으로 마일스톤을 생성하세요:\n\n작업 목록:\n{task_list}"
        )
        milestone_chain = LLMChain(llm=llm, prompt=milestone_prompt)
        milestones = milestone_chain.run(task_list=task_list)
        return {**state, "milestones": milestones}
    except Exception as e:
        logger.error(f"Error generating milestones: {str(e)}")
        return {**state, "error": f"Failed to generate milestones: {str(e)}"}

def save_results_to_markdown(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Saving results to markdown")
    try:
        if "error" in state:
            logger.warning(f"Skipping save due to previous error: {state['error']}")
            return state
        task_list = state["task_list"]
        milestones = state["milestones"]
        output_path = state.get("output_path", "project_plan.md")
        content = f"""# 프로젝트 계획\n\n## 작업 목록\n{task_list}\n\n## 마일스톤\n{milestones}\n"""
        path = Path(output_path)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Project plan saved to '{output_path}'")
        return {**state, "output_message": f"프로젝트 계획이 '{output_path}' 파일로 저장되었습니다."}
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        return {**state, "error": f"Failed to save results: {str(e)}"}

def error_handler(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.error(f"Workflow encountered an error: {state.get('error', 'Unknown error')}")
    print(f"오류가 발생했습니다: {state.get('error', '알 수 없는 오류')}")
    return state

def handle_error(state: Dict[str, Any]) -> str:
    return "error_handler" if "error" in state else "continue"

def create_workflow():
    workflow = StateGraph(ProjectData)
    
    # Add nodes
    workflow.add_node("input", input_project_details)
    workflow.add_node("generate_tasks", generate_task_list)
    workflow.add_node("generate_milestones", generate_milestones)
    workflow.add_node("save_results", save_results_to_markdown)
    workflow.add_node("error_handler", error_handler)
    
    # Add entry point - this is the critical fix
    workflow.add_edge(START, "input")
    
    # Add other edges
    workflow.add_edge("input", "generate_tasks")
    workflow.add_conditional_edges("generate_tasks", handle_error, {"continue": "generate_milestones", "error_handler": "error_handler"})
    workflow.add_conditional_edges("generate_milestones", handle_error, {"continue": "save_results", "error_handler": "error_handler"})
    workflow.add_conditional_edges("save_results", handle_error, {"continue": END, "error_handler": "error_handler"})
    workflow.add_edge("error_handler", END)
    
    return workflow.compile()

if __name__ == "__main__":
    workflow = create_workflow()
    project_text = '''
프로젝트명: Multi AI System for Home Security & Daily Conversation
    ### 프로젝트 개요
    본 프로젝트는 가정 내 보안과 일상 대화를 위한 AI 기반 멀티 시스템을 개발하는 것을 목표로 합니다.  
    ROS2를 활용하여 다양한 AI 기능을 통합하고, 웹캠과 스피커를 포함한 하드웨어와 연동하여 실시간 모니터링과 대화 기능을 제공하는 시스템을 구축합니다.  
    주요 기능으로는 낙상 감지(Fall Detection), 대시보드 기반 모니터링, AI 스피커 알림 및 대화 시스템, 그리고 LLM 기반 자동화 파이프라인이 포함됩니다.

    ---

    ### 프로젝트 주요 개발 내용

    #### 1️⃣ 프론트엔드 (대시보드 디자인)
    - 실시간 모니터링 대시보드 개발 (프레임워크 미정)
    - 낙상 감지 및 경고 시스템 시각화
    - 사용자 인터페이스(UI) 디자인 개선
    - 각 AI 모델 및 센서 데이터의 통합 디스플레이 기능 구현
    - (선택지) Streamlit, React, 또는 다른 웹 프레임워크 검토 중

    #### 2️⃣ 백엔드 (서버 설계)
    - 실시간 데이터 스트리밍 및 이벤트 처리 시스템 구축
    - WebSocket 및 REST API를 통한 대시보드와의 연동
    - 데이터베이스 설계 및 이벤트 로깅 시스템 구현
    - 사용자 인증 및 권한 관리 시스템 구축

    #### 3️⃣ ROS2 Pipeline 설계
    - ROS2 기반 모듈화된 서버 아키텍처 설계
    - 각 AI 기능을 독립적인 ROS2 노드로 구현하여 병렬 처리 최적화
    - 실시간 센서 데이터 처리 및 토픽(Pub/Sub) 관리
    - 낙상 감지, 객체 추적, 알림 시스템을 위한 개별 노드 개발
    - ROS2 서비스(Services)를 활용한 노드 상태 모니터링 및 요청 처리
    - 대시보드와의 데이터 싱크 최적화 (ApproximateTimeSynchronizer 활용)

    #### 4️⃣ 하드웨어 (웹캠 + 스피커 라즈베리파이 설계)
    - 라즈베리파이 기반의 웹캠을 활용한 영상 수집 및 처리
    - 스피커를 이용한 경고음 및 음성 알림 시스템 개발
    - 낙상 감지 시 자동 알림 및 원격 응답 기능 구현
    - 라즈베리파이를 활용한 엣지 컴퓨팅 연산 최적화

    #### 5️⃣ AI (Fall Detection Model based on Keypoints)
    - Keypoint 기반 낙상 감지 모델 개발
    - YOLO 기반 객체 감지 및 다중 객체 추적(MOT) 연동
    - 포즈 추정 데이터(Top-Down 방식) 활용하여 낙상 여부 판단
    - 데이터 수집 및 모델 학습을 통한 성능 최적화

    #### 6️⃣ LLM Pipeline 설계
    - LangGraph 기반 LLM 파이프라인 구축
    - DeepSeek-R1을 활용한 프로젝트 계획 자동화
    - 작업(Task) 생성 및 마일스톤 자동 생성 기능 구현
    - Markdown 형식으로 프로젝트 계획 자동 저장
    - 추후 LLM을 활용한 가정 내 음성 어시스턴트 기능 추가 예정

    ---

    본 프로젝트는 ROS2의 강력한 병렬 처리 기능을 활용하여 AI 기반 가정 보안 시스템을 최적화하고, LangGraph를 이용한 LLM 기반 자동화 파이프라인을 구축하여 효율적인 운영을 목표로 합니다.

'''
    
    try:
        # ✅ 올바른 입력 형식 적용
        initial_state = {"project_info": project_text}
        result = workflow.invoke(initial_state)
        if "error" in result:
            print(f"워크플로우가 오류와 함께 완료되었습니다: {result['error']}")
        else:
            print(result.get("output_message", "워크플로우가 성공적으로 완료되었습니다."))
    except Exception as e:
        print(f"워크플로우 실행 중 예외가 발생했습니다: {str(e)}")
