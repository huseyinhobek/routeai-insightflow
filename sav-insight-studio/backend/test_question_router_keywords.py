"""
Tests for Question Router keyword forcing and mode selection
"""
import pytest
from services.question_router_service import question_router_service
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_structured_keywords_enforce_structured_mode(db: Session, sample_dataset_id: str):
    """
    Test that questions with structured keywords (distribution, count, %, etc.)
    are routed to structured mode
    """
    # Test questions with structured intent keywords
    structured_questions = [
        "What is the distribution of QV3_10? Give counts and % valid.",
        "Compare Baby Boomers (60+) vs total sample for QV3_10. Return % valid by option.",
        "What percentage of respondents selected option 1?",
        "How many people chose 'Very satisfied'?",
        "Show me the frequency breakdown by age group",
        "QV3_10'in dağılımı nedir? Sayı ve yüzde göster."
    ]
    
    for question_text in structured_questions:
        routing_result = await question_router_service.route_question(
            db=db,
            dataset_id=sample_dataset_id,
            audience_id=None,
            question_text=question_text
        )
        
        assert routing_result['mode'] == 'structured', f"Question should route to structured: {question_text}"
        assert routing_result.get('mapping_debug_json', {}).get('structured_intent') == True


@pytest.mark.asyncio
async def test_rag_keywords_enforce_rag_mode(db: Session, sample_dataset_id: str):
    """
    Test that exploratory questions (why, describe, themes) are routed to RAG mode
    """
    rag_questions = [
        "Why do Baby Boomers say they are not aware of the brand? Summarize themes with quotes.",
        "What frustrations do respondents mention about energy providers?",
        "Describe the main complaints about customer service.",
        "Kullanıcılar marka hakkında ne düşünüyor? Nedenleri neler?"
    ]
    
    for question_text in rag_questions:
        routing_result = await question_router_service.route_question(
            db=db,
            dataset_id=sample_dataset_id,
            audience_id=None,
            question_text=question_text
        )
        
        assert routing_result['mode'] == 'rag', f"Question should route to RAG: {question_text}"


@pytest.mark.asyncio
async def test_var_code_hard_map(db: Session, sample_dataset_id: str, sample_variable_code: str):
    """
    Test that questions explicitly mentioning a variable code are hard-mapped to structured mode
    """
    question_text = f"Within Baby Boomers (60+), what is the distribution of {sample_variable_code}? Give counts and % valid."
    
    routing_result = await question_router_service.route_question(
        db=db,
        dataset_id=sample_dataset_id,
        audience_id=None,
        question_text=question_text
    )
    
    assert routing_result['mode'] == 'structured'
    assert routing_result.get('mapping_debug_json', {}).get('hard_mapped') == True
    assert len(routing_result.get('mapped_variables', [])) > 0


@pytest.mark.asyncio
async def test_breakdown_detection(db: Session, sample_dataset_id: str):
    """
    Test that "X by Y" patterns are detected and group_by_variable_id is set
    """
    question_text = "QV3_10 by AGE_GENDER_USA"
    
    routing_result = await question_router_service.route_question(
        db=db,
        dataset_id=sample_dataset_id,
        audience_id=None,
        question_text=question_text
    )
    
    group_by_id = routing_result.get('group_by_variable_id')
    assert group_by_id is not None, "Breakdown pattern should be detected"
    assert routing_result.get('mapping_debug_json', {}).get('group_by_variable_id') == group_by_id


# Pytest fixtures (to be implemented based on test setup)
@pytest.fixture
def db():
    """Database session fixture"""
    # TODO: Implement with test database
    pass


@pytest.fixture
def sample_dataset_id():
    """Sample dataset ID fixture"""
    # TODO: Create test dataset
    return "test-dataset-id"


@pytest.fixture
def sample_variable_code():
    """Sample variable code fixture"""
    return "QV3_10"

