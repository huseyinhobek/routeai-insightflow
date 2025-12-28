"""
Suggested questions service
Research playbook-based question suggestions (deterministic, not LLM)
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from models import Variable, Dataset
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class SuggestedQuestionsService:
    """Service for generating suggested questions based on research playbook"""
    
    def __init__(self):
        pass
    
    def get_demographic_questions(
        self,
        db: Session,
        dataset_id: str
    ) -> List[Dict[str, Any]]:
        """Get demographic questions"""
        if not DATABASE_AVAILABLE:
            return []
        
        variables = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            Variable.is_demographic == True
        ).limit(10).all()
        
        questions = []
        for var in variables:
            question_text = f"What is the distribution of {var.label or var.code}?"
            questions.append({
                "question_text": question_text,
                "variable_code": var.code,
                "category": "demographics"
            })
        
        return questions
    
    def get_kpi_questions(
        self,
        db: Session,
        dataset_id: str
    ) -> List[Dict[str, Any]]:
        """Get KPI questions (satisfaction, NPS, etc.)"""
        if not DATABASE_AVAILABLE:
            return []
        
        # Look for KPI keywords in variable labels
        kpi_keywords = ['satisfaction', 'nps', 'recommend', 'likelihood', 'value', 'trust', 'loyalty', 'memnuniyet', 'tavsiye']
        
        variables = db.query(Variable).filter(
            Variable.dataset_id == dataset_id
        ).all()
        
        # Filter by var_type in Python (since column might not exist yet)
        variables = [v for v in variables if getattr(v, 'var_type', None) in ['single_choice', 'scale']]
        
        questions = []
        for var in variables:
            label_lower = (var.label or '').lower()
            question_text_lower = (var.question_text or '').lower()
            
            if any(keyword in label_lower or keyword in question_text_lower for keyword in kpi_keywords):
                question_text = f"What is the {var.label or var.code} level?"
                questions.append({
                    "question_text": question_text,
                    "variable_code": var.code,
                    "category": "kpis"
                })
        
        return questions[:5]  # Top 5
    
    def get_driver_questions(
        self,
        db: Session,
        dataset_id: str
    ) -> List[Dict[str, Any]]:
        """Get driver questions (why questions, open-text)"""
        if not DATABASE_AVAILABLE:
            return []
        
        # Look for open-text variables with why/reason keywords
        why_keywords = ['why', 'reason', 'describe', 'explain', 'neden', 'açıkla']
        
        variables = db.query(Variable).filter(
            Variable.dataset_id == dataset_id
        ).all()
        
        # Filter by var_type in Python (since column might not exist yet)
        variables = [v for v in variables if getattr(v, 'var_type', None) == 'text']
        
        questions = []
        for var in variables:
            label_lower = (var.label or '').lower()
            question_text_lower = (var.question_text or '').lower()
            
            if any(keyword in label_lower or keyword in question_text_lower for keyword in why_keywords):
                question_text = f"Why did respondents {var.label or var.code}?"
                questions.append({
                    "question_text": question_text,
                    "variable_code": var.code,
                    "category": "drivers"
                })
        
        return questions[:5]  # Top 5
    
    def get_comparison_questions(
        self,
        db: Session,
        dataset_id: str,
        audience_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get comparison questions (breakdown by demographics)"""
        if not DATABASE_AVAILABLE:
            return []
        
        # Get top demographic and top KPI variables
        demographic_vars = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            Variable.is_demographic == True
        ).limit(3).all()
        
        kpi_keywords = ['satisfaction', 'nps', 'recommend']
        kpi_vars = db.query(Variable).filter(
            Variable.dataset_id == dataset_id
        ).limit(10).all()
        
        # Filter by var_type in Python (since column might not exist yet)
        kpi_vars = [v for v in kpi_vars if getattr(v, 'var_type', None) in ['single_choice', 'scale']][:3]
        
        # Filter KPI vars
        kpi_vars = [v for v in kpi_vars if any(kw in (v.label or '').lower() for kw in kpi_keywords)]
        
        questions = []
        for kpi_var in kpi_vars:
            for demo_var in demographic_vars:
                question_text = f"{kpi_var.label or kpi_var.code} by {demo_var.label or demo_var.code}"
                questions.append({
                    "question_text": question_text,
                    "variable_code": kpi_var.code,
                    "breakdown_variable_code": demo_var.code,
                    "category": "comparisons"
                })
        
        return questions[:5]  # Top 5
    
    def get_suggested_questions(
        self,
        db: Session,
        dataset_id: str,
        audience_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all suggested questions organized by category
        
        Returns:
            Dict with keys: demographics, kpis, drivers, comparisons
        """
        return {
            "demographics": self.get_demographic_questions(db, dataset_id),
            "kpis": self.get_kpi_questions(db, dataset_id),
            "drivers": self.get_driver_questions(db, dataset_id),
            "comparisons": self.get_comparison_questions(db, dataset_id, audience_id)
        }


# Singleton instance
suggested_questions_service = SuggestedQuestionsService()

