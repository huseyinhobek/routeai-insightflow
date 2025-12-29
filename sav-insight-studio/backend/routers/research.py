"""
Research Workflow API endpoints
Audiences, Threads, Questions, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging
import threading

from database import get_db, DATABASE_AVAILABLE
from models import (
    Dataset, Audience, AudienceMember, Thread, ThreadQuestion, ThreadResult,
    CacheAnswer, User, Variable, Utterance, Embedding
)
from auth.dependencies import get_current_user_optional
from middleware.org_scope import get_org_id_from_request
from services.audience_service import audience_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/audiences")
async def create_audience(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Create a new audience from smart filter"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    dataset_id = body.get("dataset_id")
    name = body.get("name", "")
    description = body.get("description", "")
    filter_json = body.get("filter_json")
    
    if not dataset_id or not filter_json:
        raise HTTPException(status_code=400, detail="dataset_id and filter_json are required")
    
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create audience
    audience_id = str(uuid.uuid4())
    audience = Audience(
        id=audience_id,
        dataset_id=dataset_id,
        name=name,
        description=description,
        filter_json=filter_json,
        size_n=0,  # Will be computed by refresh_membership
        active_membership_version=1,
        share_token=str(uuid.uuid4())
    )
    
    db.add(audience)
    db.commit()
    db.refresh(audience)
    
    # Materialize membership (inline for now; can be moved to background task for large datasets)
    try:
        refresh_result = audience_service.refresh_audience_membership(db=db, audience_id=audience_id)
        # Update size_n from refresh result
        audience.size_n = refresh_result.get('size_n', 0)
        db.commit()
        db.refresh(audience)
    except Exception as e:
        logger.warning(f"Failed to refresh audience membership on create: {e}")
        # Continue without membership materialization for now
    
    return {
        "id": audience.id,
        "dataset_id": audience.dataset_id,
        "name": audience.name,
        "description": audience.description,
        "size_n": audience.size_n,
        "created_at": audience.created_at.isoformat() if audience.created_at else None
    }


@router.get("/audiences")
async def list_audiences(
    request: Request,
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """List audiences, optionally filtered by dataset_id"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    query = db.query(Audience)
    
    if dataset_id:
        query = query.filter(Audience.dataset_id == dataset_id)
    
    audiences = query.order_by(Audience.created_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "dataset_id": a.dataset_id,
            "name": a.name,
            "description": a.description,
            "size_n": a.size_n,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None
        }
        for a in audiences
    ]


@router.get("/audiences/{audience_id}")
async def get_audience(
    audience_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get audience details"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    audience = db.query(Audience).filter(Audience.id == audience_id).first()
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    
    return {
        "id": audience.id,
        "dataset_id": audience.dataset_id,
        "name": audience.name,
        "description": audience.description,
        "filter_json": audience.filter_json,
        "size_n": audience.size_n,
        "active_membership_version": audience.active_membership_version,
        "share_token": audience.share_token,
        "created_at": audience.created_at.isoformat() if audience.created_at else None,
        "updated_at": audience.updated_at.isoformat() if audience.updated_at else None
    }


@router.put("/audiences/{audience_id}")
async def update_audience(
    audience_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Update audience"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    audience = db.query(Audience).filter(Audience.id == audience_id).first()
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    
    filter_json_changed = False
    if "name" in body:
        audience.name = body["name"]
    if "description" in body:
        audience.description = body["description"]
    if "filter_json" in body:
        if audience.filter_json != body["filter_json"]:
            filter_json_changed = True
        audience.filter_json = body["filter_json"]
    
    audience.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(audience)
    
    # Refresh membership if filter_json changed
    if filter_json_changed:
        try:
            refresh_result = audience_service.refresh_audience_membership(db=db, audience_id=audience_id)
            # Update size_n from refresh result
            audience.size_n = refresh_result.get('size_n', 0)
            db.commit()
            db.refresh(audience)
        except Exception as e:
            logger.warning(f"Failed to refresh audience membership on update: {e}")
            # Continue without membership refresh for now
    
    return {
        "id": audience.id,
        "name": audience.name,
        "description": audience.description,
        "updated_at": audience.updated_at.isoformat() if audience.updated_at else None
    }


@router.delete("/audiences/{audience_id}")
async def delete_audience(
    audience_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Delete audience"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    audience = db.query(Audience).filter(Audience.id == audience_id).first()
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    
    db.delete(audience)
    db.commit()
    
    return {"success": True, "message": "Audience deleted"}


@router.post("/audiences/{audience_id}/refresh-membership")
async def refresh_audience_membership(
    audience_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Refresh audience membership (atomic swap pattern)
    This should be a background task in production
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    audience = db.query(Audience).filter(Audience.id == audience_id).first()
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")
    
    # Execute atomic swap membership refresh
    try:
        result = audience_service.refresh_audience_membership(db, audience_id)
        return {
            "audience_id": audience_id,
            "status": "success",
            "version": result["version"],
            "size_n": result["size_n"]
        }
    except Exception as e:
        logger.error(f"Error refreshing audience membership: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh membership: {str(e)}")


# ==================== THREADS CRUD ====================

@router.post("/threads")
async def create_thread(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Create a new thread"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    dataset_id = body.get("dataset_id")
    audience_id = body.get("audience_id")  # Optional
    title = body.get("title", "")
    
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Verify audience exists if provided
    if audience_id:
        audience = db.query(Audience).filter(Audience.id == audience_id).first()
        if not audience:
            raise HTTPException(status_code=404, detail="Audience not found")
        if audience.dataset_id != dataset_id:
            raise HTTPException(status_code=400, detail="Audience does not belong to dataset")
    
    # Create thread
    thread_id = str(uuid.uuid4())
    thread = Thread(
        id=thread_id,
        dataset_id=dataset_id,
        audience_id=audience_id,
        title=title or f"Thread {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        status="ready",
        share_token=str(uuid.uuid4())
    )
    
    db.add(thread)
    db.commit()
    db.refresh(thread)
    
    return {
        "id": thread.id,
        "dataset_id": thread.dataset_id,
        "audience_id": thread.audience_id,
        "title": thread.title,
        "status": thread.status,
        "created_at": thread.created_at.isoformat() if thread.created_at else None
    }


@router.get("/threads")
async def list_threads(
    request: Request,
    dataset_id: Optional[str] = None,
    audience_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """List threads, optionally filtered by dataset_id and/or audience_id"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    query = db.query(Thread)
    
    if dataset_id:
        query = query.filter(Thread.dataset_id == dataset_id)
    if audience_id:
        query = query.filter(Thread.audience_id == audience_id)
    
    threads = query.order_by(Thread.updated_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "dataset_id": t.dataset_id,
            "audience_id": t.audience_id,
            "title": t.title,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        }
        for t in threads
    ]


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get thread details including questions and results"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get questions with results
    questions = db.query(ThreadQuestion).filter(
        ThreadQuestion.thread_id == thread_id
    ).order_by(ThreadQuestion.created_at.asc()).all()
    
    questions_data = []
    for q in questions:
        question_data = {
            "id": q.id,
            "question_text": q.question_text,
            "normalized_question": q.normalized_question,
            "mode": q.mode,
            "status": q.status,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "mapped_variable_ids": q.mapped_variable_ids,
            "negation_flags_json": q.negation_flags_json
        }
        
        # Get result if exists
        if q.result:
            question_data["result"] = {
                "id": q.result.id,
                "narrative_text": q.result.narrative_text,
                "evidence_json": q.result.evidence_json,
                "chart_json": q.result.chart_json,
                "mapping_debug_json": q.result.mapping_debug_json,
                "created_at": q.result.created_at.isoformat() if q.result.created_at else None
            }
        
        questions_data.append(question_data)
    
    return {
        "id": thread.id,
        "dataset_id": thread.dataset_id,
        "audience_id": thread.audience_id,
        "title": thread.title,
        "status": thread.status,
        "share_token": thread.share_token,
        "last_error": thread.last_error,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
        "questions": questions_data
    }


@router.put("/threads/{thread_id}")
async def update_thread(
    thread_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Update thread"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if "title" in body:
        thread.title = body["title"]
    if "status" in body:
        thread.status = body["status"]
    
    thread.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(thread)
    
    return {
        "id": thread.id,
        "title": thread.title,
        "status": thread.status,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None
    }


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Delete thread"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    db.delete(thread)
    db.commit()
    
    return {"success": True, "message": "Thread deleted"}


@router.post("/threads/{thread_id}/share")
async def create_thread_share_token(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Create or regenerate share token for thread"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    thread.share_token = str(uuid.uuid4())
    thread.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(thread)
    
    return {
        "thread_id": thread.id,
        "share_token": thread.share_token
    }


# ==================== THREAD QUESTIONS ====================

@router.post("/threads/{thread_id}/questions")
async def add_thread_question(
    thread_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Add a question to a thread and process it
    This should trigger background job in production, but for now synchronous
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    question_text = body.get("question_text", "")
    if not question_text:
        raise HTTPException(status_code=400, detail="question_text is required")
    
    # Import services
    from services.question_router_service import question_router_service
    from services.structured_aggregation_service import structured_aggregation_service
    from services.rag_service import rag_service
    from services.narration_service import narration_service
    from services.cache_service import cache_service
    from services.decision_proxy_service import decision_proxy_service
    from models import ThreadQuestion, ThreadResult, Dataset
    
    # Get dataset version
    dataset = db.query(Dataset).filter(Dataset.id == thread.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    dataset_version = dataset.version or 1
    
    # Normalize question
    normalized_question = question_router_service.normalize_question(question_text)
    
    # Create thread question
    thread_question = ThreadQuestion(
        thread_id=thread_id,
        question_text=question_text,
        normalized_question=normalized_question,
        status="processing"
    )
    db.add(thread_question)
    try:
        db.commit()
        db.refresh(thread_question)
    except Exception as commit_error:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating thread question: {str(commit_error)}")
    
    try:
        # Route question (this might use the same db session, so catch any SQL errors)
        try:
            routing_result = await question_router_service.route_question(
                db=db,
                dataset_id=thread.dataset_id,
                audience_id=thread.audience_id,
                question_text=question_text
            )
        except Exception as route_error:
            # If routing fails, rollback to clear transaction state
            try:
                db.rollback()
            except:
                pass
            logger.error(f"Error in route_question: {route_error}", exc_info=True)
            # Re-raise to be caught by outer exception handler
            raise route_error
        
        mode = routing_result['mode']
        mapped_variables = routing_result.get('mapped_variables', [])
        group_by_variable_id = routing_result.get('group_by_variable_id')
        comparison_audience_id = routing_result.get('comparison_audience_id')
        override_audience_id = routing_result.get('override_audience_id')  # Get override from router
        negation_ast = routing_result.get('negation_flags', {})
        mapping_debug_json = routing_result.get('mapping_debug_json', {})
        
        # Use override_audience_id if specified, otherwise use thread.audience_id
        effective_audience_id = override_audience_id if override_audience_id is not None else thread.audience_id
        
        # Generate cache key with mode and mapped variables (router result required)
        import hashlib
        import json
        cache_key_parts = [
            thread.dataset_id,
            str(dataset_version),
            effective_audience_id or '',  # Use effective_audience_id for cache key
            normalized_question,
            mode,
            json.dumps(sorted(mapped_variables), sort_keys=True),  # Sorted for consistency
            str(group_by_variable_id) if group_by_variable_id else '',
            str(comparison_audience_id) if comparison_audience_id else ''  # Add comparison_audience_id to cache key
        ]
        cache_key_hash = hashlib.sha256('|'.join(cache_key_parts).encode('utf-8')).hexdigest()
        
        # Check cache (using key_hash directly since we have mode now)
        from models import CacheAnswer
        cache_entry = db.query(CacheAnswer).filter(CacheAnswer.key_hash == cache_key_hash).first()
        if cache_entry:
            # Cache hit - reuse existing result by creating a new ThreadResult linked to this question
            cached_result = db.query(ThreadResult).filter(ThreadResult.id == cache_entry.thread_result_id).first()
            if cached_result:
                # For structured mode, always regenerate chart_json from evidence_json
                # to ensure chart format is always up-to-date (chart generation logic may evolve)
                cached_chart_json = cached_result.chart_json
                if mode == "structured" and mapped_variables and cached_result.evidence_json:
                    variable_id = mapped_variables[0]
                    variable = db.query(Variable).filter(Variable.id == variable_id).first()
                    if variable:
                        cached_chart_json = structured_aggregation_service.generate_chart_json(
                            evidence_json=cached_result.evidence_json,
                            variable_type=variable.var_type if variable else 'single_choice'
                        )
                
                # Create a new ThreadResult linked to this question (copy from cached result)
                thread_result = ThreadResult(
                    thread_question_id=thread_question.id,
                    dataset_version=dataset_version,
                    evidence_json=cached_result.evidence_json,
                    chart_json=cached_chart_json,  # Use regenerated chart_json for structured mode
                    narrative_text=cached_result.narrative_text,
                    citations_json=cached_result.citations_json,
                    mapping_debug_json=cached_result.mapping_debug_json,
                    model_info_json=cached_result.model_info_json
                )
                db.add(thread_result)
                try:
                    db.commit()
                    db.refresh(thread_result)
                except Exception as commit_error:
                    db.rollback()
                    raise commit_error
                
                # Update thread question status
                thread_question.mode = mode
                thread_question.mapped_variable_ids = mapped_variables
                thread_question.negation_flags_json = negation_ast
                thread_question.status = "ready"
                thread.status = "ready"
                thread.updated_at = datetime.utcnow()
                try:
                    db.commit()
                except Exception as commit_error:
                    db.rollback()
                    raise commit_error
                
                return {
                    "thread_question_id": thread_question.id,
                    "mode": mode,
                    "status": "ready",
                    "cached": True,
                    "result": {
                        "narrative_text": thread_result.narrative_text,
                        "evidence_json": thread_result.evidence_json,
                        "chart_json": thread_result.chart_json,  # Use regenerated chart_json
                        "mapping_debug_json": thread_result.mapping_debug_json
                    }
                }
        
        # Update thread question with mode
        thread_question.mode = mode
        thread_question.mapped_variable_ids = mapped_variables
        thread_question.negation_flags_json = negation_ast
        try:
            db.commit()
        except Exception as commit_error:
            db.rollback()
            logger.error(f"Error committing thread question update: {commit_error}", exc_info=True)
            raise commit_error
        
        # Initialize chart_json for response (will be set in structured mode)
        response_chart_json = None
        
        # Process based on mode
        if mode == "decision_proxy":
            # Decision proxy mode - handle normative/decision questions
            decision_result = await decision_proxy_service.answer_decision_question(
                db=db,
                dataset_id=thread.dataset_id,
                audience_id=effective_audience_id,
                question_text=question_text,
                router_payload=routing_result
            )
            
            # Extract components from decision result
            evidence_json = decision_result.get("evidence_json", {})
            narrative_text = decision_result.get("narrative_text", "")
            proxy_answer = decision_result.get("proxy_answer", {})
            decision_rules = decision_result.get("decision_rules", [])
            clarifying_controls = decision_result.get("clarifying_controls", {})
            next_best_questions = decision_result.get("next_best_questions", [])
            citations_json = decision_result.get("citations_json", [])
            debug_json_combined = {
                **(mapping_debug_json or {}),
                **(decision_result.get("debug_json", {}))
            }
            
            # Create thread result
            thread_result = ThreadResult(
                thread_question_id=thread_question.id,
                dataset_version=dataset_version,
                evidence_json={
                    **evidence_json,
                    "proxy_answer": proxy_answer,
                    "decision_rules": decision_rules,
                    "clarifying_controls": clarifying_controls,
                    "next_best_questions": next_best_questions
                },
                narrative_text=narrative_text,
                citations_json=citations_json,
                mapping_debug_json=debug_json_combined,
                model_info_json={"model": "decision_proxy"}
            )
            db.add(thread_result)
            try:
                db.commit()
                db.refresh(thread_result)
            except Exception as commit_error:
                db.rollback()
                raise commit_error
            
        elif mode == "structured" and mapped_variables:
            # Structured aggregation
            variable_id = mapped_variables[0]
            
            # Check if comparison is needed
            if comparison_audience_id:
                # Compare audience vs total sample
                evidence_json = structured_aggregation_service.compare_audience_vs_total(
                    db=db,
                    variable_id=variable_id,
                    audience_id=comparison_audience_id,
                    dataset_id=thread.dataset_id,
                    negation_ast=negation_ast
                )
            # Check if breakdown is needed
            elif group_by_variable_id:
                evidence_json = structured_aggregation_service.aggregate_with_breakdown(
                    db=db,
                    variable_id=variable_id,
                    group_by_variable_id=group_by_variable_id,
                    dataset_id=thread.dataset_id,
                    audience_id=effective_audience_id,  # Use effective_audience_id
                    negation_ast=negation_ast
                )
            else:
                evidence_json = structured_aggregation_service.aggregate_single_choice(
                    db=db,
                    variable_id=variable_id,
                    dataset_id=thread.dataset_id,
                    audience_id=effective_audience_id,  # Use effective_audience_id
                    negation_ast=negation_ast
                )
            
            # Generate chart
            variable = db.query(Variable).filter(Variable.id == variable_id).first()
            chart_json = structured_aggregation_service.generate_chart_json(
                evidence_json=evidence_json,
                variable_type=variable.var_type if variable else 'single_choice'
            )
            
            # Store chart_json for response
            response_chart_json = chart_json
            
            # Check if variable is Tier3 (knowledge/awareness) for interpretation_disclaimer
            interpretation_disclaimer = None
            variable_tier = None
            if variable:
                from services.decision_proxy_service import decision_proxy_service
                var_text = (variable.question_text or variable.label or variable.code or '').lower()
                
                # Determine tier
                if any(kw in var_text for kw in decision_proxy_service.tier0_keywords):
                    variable_tier = 0
                elif any(kw in var_text for kw in decision_proxy_service.tier1_keywords):
                    variable_tier = 1
                elif any(kw in var_text for kw in decision_proxy_service.tier2_keywords):
                    variable_tier = 2
                elif any(kw in var_text for kw in decision_proxy_service.tier3_keywords):
                    variable_tier = 3
                
                # For Tier3, get full copy pack
                if variable_tier == 3:
                    base_n = evidence_json.get('base_n', 0)
                    interpretation_disclaimer = decision_proxy_service.get_proxy_copy(
                        tier=3,
                        locale='en',
                        severity='risk',
                        low_confidence_flag=True,
                        base_n=base_n,
                        top2_gap_pp=0.0
                    )['limitation_statement']
                    # Add to evidence_json
                    evidence_json['interpretation_disclaimer'] = interpretation_disclaimer
                    evidence_json['variable_tier'] = 3
                    evidence_json['variable_tier_name'] = 'Knowledge/Awareness'
                    evidence_json['proxy_copy'] = decision_proxy_service.get_proxy_copy(
                        tier=3,
                        locale='en',
                        severity='risk',
                        low_confidence_flag=True,
                        base_n=base_n,
                        top2_gap_pp=0.0
                    )
            
            # Generate narrative
            narrative_result = narration_service.validate_and_generate(
                evidence_json=evidence_json,
                question_text=question_text,
                mode="structured"
            )
            
            narrative_text = narrative_result['narrative_text']
            
            # Add disclaimer to narrative if Tier3
            if interpretation_disclaimer:
                narrative_text = f"⚠️ {interpretation_disclaimer}\n\n{narrative_text}"
            
            # Create thread result
            thread_result = ThreadResult(
                thread_question_id=thread_question.id,
                dataset_version=dataset_version,
                evidence_json=evidence_json,
                chart_json=chart_json,
                narrative_text=narrative_text,
                mapping_debug_json=mapping_debug_json,
                model_info_json={"model": "structured"}
            )
            db.add(thread_result)
            try:
                db.commit()
                db.refresh(thread_result)
            except Exception as commit_error:
                db.rollback()
                raise commit_error
            
        else:
            # RAG mode
            variable_id = mapped_variables[0] if mapped_variables else None
            utterances = rag_service.retrieve_utterances(
                db=db,
                dataset_id=thread.dataset_id,
                question_text=question_text,
                audience_id=effective_audience_id,  # Use effective_audience_id
                variable_id=variable_id
            )
            
            evidence_json = rag_service.build_evidence_json(utterances, question_text)
            retrieved_count = evidence_json.get("retrieved_count", 0)

            if retrieved_count == 0:
                # RAG not ready or genuinely no matching responses.
                # Return an explicit narrative so the user understands why they see no quotes.
                narrative_text = (
                    "No matching utterances were retrieved for this question. "
                    "This may mean utterances/embeddings are not yet generated for this dataset, "
                    "or there are genuinely no responses matching the query in the current audience."
                )
                narrative_result = {
                    "narrative_text": narrative_text,
                    "errors": [],
                    "is_valid": True,
                }
            else:
                synthesis = await rag_service.synthesize_with_llm(evidence_json, question_text)
                
                # Pass synthesis result to evidence_json for narration
                evidence_json['synthesis_result'] = synthesis
                
                narrative_result = narration_service.validate_and_generate(
                    evidence_json=evidence_json,
                    question_text=question_text,
                    mode="rag"
                )
                
                narrative_text = narrative_result['narrative_text']
            
            # Create thread result
            thread_result = ThreadResult(
                thread_question_id=thread_question.id,
                dataset_version=dataset_version,
                evidence_json=evidence_json,
                narrative_text=narrative_text,
                citations_json=evidence_json.get('citations', []),
                mapping_debug_json=mapping_debug_json,
                model_info_json={"model": "rag"}
            )
            db.add(thread_result)
            try:
                db.commit()
                db.refresh(thread_result)
            except Exception as commit_error:
                db.rollback()
                raise commit_error
        
        # Cache the result (use same cache key hash)
        try:
            from models import CacheAnswer
            existing_cache = db.query(CacheAnswer).filter(CacheAnswer.key_hash == cache_key_hash).first()
            if existing_cache:
                existing_cache.thread_result_id = thread_result.id
            else:
                cache_entry = CacheAnswer(
                    dataset_id=thread.dataset_id,
                    dataset_version=dataset_version,
                    audience_id=thread.audience_id,
                    normalized_question=normalized_question,
                    mode=mode,
                    key_hash=cache_key_hash,
                    thread_result_id=thread_result.id
                )
                db.add(cache_entry)
            db.commit()
        except Exception as cache_error:
            logger.warning(f"Failed to cache result: {cache_error}")
            # Don't fail the request if caching fails
        
        # Update thread question status
        thread_question.status = "ready"
        thread.status = "ready"
        thread.updated_at = datetime.utcnow()
        try:
            db.commit()
        except Exception as commit_error:
            db.rollback()
            raise commit_error
        
        # Prepare result response
        if mode == "decision_proxy":
            # Decision proxy mode has special structure
            result_data = {
                "narrative_text": narrative_text,
                "evidence_json": evidence_json,
                "proxy_answer": evidence_json.get("proxy_answer", {}),
                "decision_rules": evidence_json.get("decision_rules", []),
                "clarifying_controls": evidence_json.get("clarifying_controls", {}),
                "next_best_questions": evidence_json.get("next_best_questions", []),
                "mapping_debug_json": debug_json_combined if 'debug_json_combined' in locals() else mapping_debug_json
            }
        else:
            result_data = {
                "narrative_text": narrative_text,
                "evidence_json": evidence_json,
                "mapping_debug_json": mapping_debug_json
            }
            
            # Add chart_json if it exists (structured mode only)
            if response_chart_json is not None:
                result_data["chart_json"] = response_chart_json
        
        return {
            "thread_question_id": thread_question.id,
            "mode": mode,
            "status": "ready",
            "result": result_data
        }
        
    except Exception as e:
        logger.error(f"Error processing thread question: {e}", exc_info=True)
        db.rollback()  # Rollback any failed transaction
        try:
            # Try to update thread question status if it was created
            if 'thread_question' in locals() and thread_question.id:
                thread_question.status = "error"
                thread.status = "error"
                thread.last_error = str(e)
                db.commit()
        except Exception as update_error:
            logger.error(f"Error updating thread status: {update_error}", exc_info=True)
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


# ==================== SUGGESTED QUESTIONS ====================

@router.get("/suggested-questions")
async def get_suggested_questions(
    dataset_id: str,
    audience_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get suggested questions based on research playbook"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    from services.suggested_questions_service import suggested_questions_service
    
    questions = suggested_questions_service.get_suggested_questions(
        db=db,
        dataset_id=dataset_id,
        audience_id=audience_id
    )
    
    return questions


# ==================== EMBEDDING GENERATION ====================

@router.post("/datasets/{dataset_id}/populate-data")
async def populate_dataset_data(
    dataset_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Populate Variable, ValueLabel, Respondent, and Response tables for a dataset
    This is needed if the dataset was uploaded before ingestion_service was implemented
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check if file exists
    from pathlib import Path
    from config import settings
    
    file_path = Path(dataset.file_path) if dataset.file_path else None
    if not file_path or not file_path.exists():
        # Try UPLOAD_DIR
        upload_dir = Path(settings.UPLOAD_DIR)
        file_path = upload_dir / Path(dataset.file_path).name if dataset.file_path else None
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Dataset file not found")
    
    # Load file
    from main import load_file_to_dataframe
    df, meta = load_file_to_dataframe(file_path)
    
    if df is None or meta is None:
        raise HTTPException(status_code=500, detail="Failed to load dataset file")
    
    # Get variables metadata
    variables = dataset.variables_meta or []
    
    # Run ingestion
    from services.ingestion_service import ingestion_service
    try:
        result = ingestion_service.populate_respondents_and_responses(
            db=db,
            dataset_id=dataset_id,
            df=df,
            variables=variables,
            meta=meta
        )
        
        # Enqueue Celery tasks for utterance and embedding generation
        try:
            from tasks.research_tasks import (
                generate_utterances_for_dataset,
                generate_embeddings_for_variables,
                generate_embeddings_for_utterances
            )
            # Trigger background jobs
            generate_utterances_for_dataset.delay(dataset_id)
            generate_embeddings_for_variables.delay(dataset_id)
            # Note: generate_embeddings_for_utterances will be triggered after utterances are generated
        except Exception as celery_err:
            logger.warning(f"Failed to enqueue Celery tasks for dataset {dataset_id}: {celery_err}")
            # Continue without background jobs if Celery is not available
        
        return {
            "dataset_id": dataset_id,
            "result": result,
            "message": "Data populated successfully"
        }
    except Exception as e:
        logger.error(f"Error populating dataset data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to populate data: {str(e)}")


# Global dictionary to track active embedding generation threads
# Key: dataset_id, Value: thread object
_active_embedding_threads = {}
_thread_lock = threading.Lock()

def _start_embedding_generation_thread(dataset_id: str) -> bool:
    """
    Start embedding generation in a background thread if not already running.
    Returns True if thread was started, False if already running.
    """
    import threading
    from database import SessionLocal
    from services.embedding_service import embedding_service
    
    with _thread_lock:
        # Check if thread is already running for this dataset
        if dataset_id in _active_embedding_threads:
            thread = _active_embedding_threads[dataset_id]
            if thread.is_alive():
                logger.debug(f"Embedding generation already running for dataset {dataset_id}")
                return False
            else:
                # Thread died, remove it
                del _active_embedding_threads[dataset_id]
    
    def _run_embedding_generation():
        """Run embedding generation in a separate thread"""
        try:
            # Create a new DB session for this thread
            thread_db = SessionLocal()
            try:
                # Generate embeddings for variables first
                var_result = embedding_service.generate_embeddings_for_variables(
                    db=thread_db, 
                    dataset_id=dataset_id
                )
                logger.info(f"Generated variable embeddings for dataset {dataset_id}: {var_result}")
                
                # Generate embeddings for utterances (if utterances exist)
                utterance_result = embedding_service.generate_embeddings_for_utterances(
                    db=thread_db, 
                    dataset_id=dataset_id
                )
                logger.info(f"Generated utterance embeddings for dataset {dataset_id}: {utterance_result}")
            finally:
                thread_db.close()
        except Exception as e:
            logger.error(f"Error generating embeddings for dataset {dataset_id}: {e}", exc_info=True)
        finally:
            # Remove thread from active threads when done
            with _thread_lock:
                if dataset_id in _active_embedding_threads:
                    del _active_embedding_threads[dataset_id]
    
    # Start embedding generation in a background thread
    thread = threading.Thread(target=_run_embedding_generation, daemon=True)
    thread.start()
    
    with _thread_lock:
        _active_embedding_threads[dataset_id] = thread
    
    logger.info(f"Started background embedding generation for dataset {dataset_id}")
    return True

@router.post("/datasets/{dataset_id}/generate-embeddings")
async def generate_embeddings(
    dataset_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Generate embeddings for variables and utterances in a dataset
    This is needed for the research workflow to work properly.
    
    NOTE: This runs in a background thread to avoid blocking the API.
    The operation is idempotent - existing embeddings are skipped.
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check OpenAI API key
    from config import settings
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    
    # Start embedding generation thread (will skip if already running)
    started = _start_embedding_generation_thread(dataset_id)
    
    # Return immediately - the operation is running in background
    return {
        "dataset_id": dataset_id,
        "message": "Embedding generation started in background. Use /embedding-status endpoint to check progress." if started else "Embedding generation already running.",
        "status": "started" if started else "already_running"
    }

@router.get("/datasets/{dataset_id}/embedding-status")
async def get_embedding_status(
    dataset_id: str,
    auto_resume: bool = True,  # Automatically resume if incomplete and no active thread
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Get embedding generation status for a dataset
    Returns total utterances, embedded utterances, and progress percentage
    
    If auto_resume=True and embedding is incomplete with no active thread, automatically starts generation.
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Count total utterances for this dataset (count distinct IDs only)
    total_utterances = db.query(func.count(func.distinct(Utterance.id))).join(Variable).filter(
        Variable.dataset_id == dataset_id
    ).scalar() or 0
    
    # Count utterances that have embeddings (count distinct IDs only)
    embedded_utterances = db.query(func.count(func.distinct(Utterance.id))).join(Variable).join(
        Embedding, 
        (Embedding.object_type == 'utterance') & 
        (Embedding.object_id == Utterance.id) &
        (Embedding.dataset_id == dataset_id)
    ).filter(
        Variable.dataset_id == dataset_id
    ).scalar() or 0
    
    # Count total variables
    total_variables = db.query(Variable).filter(
        Variable.dataset_id == dataset_id
    ).count()
    
    # Count variables that have embeddings (count distinct IDs only)
    embedded_variables = db.query(func.count(func.distinct(Variable.id))).join(
        Embedding,
        (Embedding.object_type == 'variable') &
        (Embedding.object_id == Variable.id) &
        (Embedding.dataset_id == dataset_id)
    ).filter(
        Variable.dataset_id == dataset_id
    ).scalar() or 0
    
    # Calculate progress percentages (cap at 100%)
    utterance_progress = min((embedded_utterances / total_utterances * 100) if total_utterances > 0 else 0, 100.0)
    variable_progress = min((embedded_variables / total_variables * 100) if total_variables > 0 else 0, 100.0)
    
    # Overall progress (weighted average: utterances are usually more important)
    # If both exist, weight utterances 70% and variables 30%
    if total_utterances > 0 and total_variables > 0:
        overall_progress = (utterance_progress * 0.7) + (variable_progress * 0.3)
    elif total_utterances > 0:
        overall_progress = utterance_progress
    elif total_variables > 0:
        overall_progress = variable_progress
    else:
        overall_progress = 0
    
    # Cap overall progress at 100%
    overall_progress = min(overall_progress, 100.0)
    
    is_complete = embedded_utterances == total_utterances and embedded_variables == total_variables and total_utterances > 0
    
    # Auto-resume: If embedding is incomplete and no active thread, start it
    is_running = False
    if not is_complete and auto_resume:
        with _thread_lock:
            if dataset_id in _active_embedding_threads:
                thread = _active_embedding_threads[dataset_id]
                is_running = thread.is_alive()
        
        if not is_running:
            # Check OpenAI API key before auto-resuming
            from config import settings
            if settings.OPENAI_API_KEY:
                logger.info(f"Auto-resuming embedding generation for dataset {dataset_id} (incomplete: {embedded_utterances}/{total_utterances} utterances)")
                _start_embedding_generation_thread(dataset_id)
                is_running = True
            else:
                logger.warning(f"Cannot auto-resume embedding generation: OpenAI API key not configured")
    
    return {
        "dataset_id": dataset_id,
        "utterances": {
            "total": total_utterances,
            "embedded": embedded_utterances,
            "progress": round(utterance_progress, 2)
        },
        "variables": {
            "total": total_variables,
            "embedded": embedded_variables,
            "progress": round(variable_progress, 2)
        },
        "overall_progress": round(overall_progress, 2),
        "is_complete": is_complete,
        "is_running": is_running
    }

