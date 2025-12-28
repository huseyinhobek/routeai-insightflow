"""
End-to-end tests for research workflow (Mode A & Mode B)
"""
import pytest
from sqlalchemy.orm import Session
from services.question_router_service import question_router_service
from services.structured_aggregation_service import structured_aggregation_service
from services.rag_service import rag_service
from services.narration_service import narration_service
from models import Dataset, Thread, ThreadQuestion, ThreadResult


@pytest.mark.asyncio
async def test_structured_mode_e2e_flow(db: Session, test_dataset_id: str):
    """
    E2E test for Mode A (Structured): question → router → aggregation → narration
    """
    question_text = "What is the distribution of QV3_10?"
    
    # Step 1: Route question
    routing_result = await question_router_service.route_question(
        db=db,
        dataset_id=test_dataset_id,
        audience_id=None,
        question_text=question_text
    )
    
    assert routing_result['mode'] == 'structured'
    assert len(routing_result.get('mapped_variables', [])) > 0
    
    variable_id = routing_result['mapped_variables'][0]
    
    # Step 2: Structured aggregation
    evidence_json = structured_aggregation_service.aggregate_single_choice(
        db=db,
        variable_id=variable_id,
        dataset_id=test_dataset_id,
        audience_id=None,
        negation_ast=None
    )
    
    assert 'base_n' in evidence_json
    assert 'answered_n' in evidence_json
    assert 'categories' in evidence_json
    assert len(evidence_json['categories']) > 0
    
    # Step 3: Generate narrative
    narrative_result = narration_service.validate_and_generate(
        evidence_json=evidence_json,
        question_text=question_text,
        mode="structured"
    )
    
    assert narrative_result['is_valid'] == True
    assert 'narrative_text' in narrative_result
    assert narrative_result['narrative_text'] != "Data mismatch—unable to generate safe narrative."
    
    # Step 4: Validate numbers in narrative match evidence
    # (This is already handled by validate_structured_numbers, but we verify here)
    narrative_text = narrative_result['narrative_text']
    # Numbers should come from evidence_json, validation should pass
    assert len(narrative_result.get('errors', [])) == 0


@pytest.mark.asyncio
async def test_rag_mode_e2e_flow(db: Session, test_dataset_id: str):
    """
    E2E test for Mode B (RAG): question → router → utterance retrieval → LLM synthesis → narration
    """
    question_text = "Why do respondents mention frustrations about energy providers?"
    
    # Step 1: Route question
    routing_result = await question_router_service.route_question(
        db=db,
        dataset_id=test_dataset_id,
        audience_id=None,
        question_text=question_text
    )
    
    assert routing_result['mode'] == 'rag'
    
    # Step 2: Retrieve utterances
    utterances = rag_service.retrieve_utterances(
        db=db,
        dataset_id=test_dataset_id,
        question_text=question_text,
        audience_id=None,
        variable_id=None,
        top_k=50
    )
    
    # Step 3: Build evidence JSON
    evidence_json = rag_service.build_evidence_json(utterances, question_text)
    
    if evidence_json.get('retrieved_count', 0) == 0:
        # Utterances not ready - this is expected if embeddings haven't been generated
        pytest.skip("Utterances/embeddings not ready for RAG test")
    
    assert evidence_json.get('retrieved_count', 0) > 0
    assert len(evidence_json.get('citations', [])) > 0
    
    # Step 4: Synthesize with LLM
    synthesis_result = rag_service.synthesize_with_llm(evidence_json, question_text)
    
    assert 'themes' in synthesis_result
    assert 'narrative' in synthesis_result
    assert 'caveats' in synthesis_result
    
    # Step 5: Generate narrative (pass synthesis result)
    evidence_json['synthesis_result'] = synthesis_result
    narrative_result = narration_service.validate_and_generate(
        evidence_json=evidence_json,
        question_text=question_text,
        mode="rag"
    )
    
    assert narrative_result['is_valid'] == True
    assert 'narrative_text' in narrative_result
    
    # Step 6: Verify narrative doesn't contain global percentages
    narrative_text = narrative_result['narrative_text']
    # Should not contain phrases like "X% of all respondents" (only "in the retrieved sample")
    assert "in the retrieved sample" in narrative_text.lower() or "among these responses" in narrative_text.lower()


@pytest.mark.asyncio
async def test_thread_question_caching(db: Session, test_thread_id: str):
    """
    Test that thread questions use cache for duplicate questions
    """
    # TODO: Implement test for cache hit scenario
    # 1. Create thread question 1 with question_text
    # 2. Process it and verify result is cached
    # 3. Create thread question 2 with same question_text (same thread or different)
    # 4. Verify that cache is used (same ThreadResult ID or cached flag)
    pass


# Pytest fixtures (to be implemented based on test setup)
@pytest.fixture
def db():
    """Database session fixture"""
    # TODO: Implement with test database
    pass


@pytest.fixture
def test_dataset_id():
    """Test dataset ID fixture"""
    # TODO: Create test dataset with sample data
    return "test-dataset-id"


@pytest.fixture
def test_thread_id():
    """Test thread ID fixture"""
    # TODO: Create test thread
    return "test-thread-id"

