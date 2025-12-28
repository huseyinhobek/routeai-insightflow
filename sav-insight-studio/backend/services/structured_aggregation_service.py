"""
Structured aggregation service
Performs deterministic SQL-based aggregation for structured questions
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, text, func, Float, String, case
from typing import List, Dict, Any, Optional
import logging

from models import (
    Variable, ValueLabel, Response, Respondent, Audience, AudienceMember,
    Dataset
)
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class StructuredAggregationService:
    """
    Service for structured aggregation queries.
    
    IMPORTANT:
    - All statistics (counts, percentages, comparisons, breakdowns) MUST be computed
      only from `responses` / `value_labels` tables.
    - Twin Transformation outputs (`TransformResult.sentences`, `Utterance.display_text`)
      MUST NEVER be used to compute statistics. They are only for RAG / human display.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def _build_value_label_join_condition(response_value_code_column, value_label_table):
        """
        Build consistent ValueLabel join condition that handles numeric value_code
        normalization (e.g., "1" vs "1.0" matching).
        
        Uses Float cast comparison for numeric matching, which handles both
        "1" and "1.0" string representations correctly.
        
        Args:
            response_value_code_column: SQLAlchemy column reference for Response.value_code
            value_label_table: SQLAlchemy table/alias reference for ValueLabel
            
        Returns:
            SQLAlchemy binary expression for the join condition
        """
        # Normalize by casting to Float for numeric comparison
        # This handles "1" vs "1.0" correctly (both become 1.0)
        # We use CAST to Float for comparison, which is safe for numeric values
        # For non-numeric values, this will still work but may need adjustment in future
        return func.cast(response_value_code_column, Float) == func.cast(value_label_table.value_code, Float)
    
    def get_base_n(
        self,
        db: Session,
        audience_id: Optional[str],
        dataset_id: str
    ) -> int:
        """
        Get base_n (total respondents in audience)
        """
        if audience_id:
            # Get from audience_members with active version
            audience = db.query(Audience).filter(Audience.id == audience_id).first()
            if not audience:
                raise ValueError(f"Audience {audience_id} not found")
            
            count = db.query(AudienceMember).filter(
                and_(
                    AudienceMember.audience_id == audience_id,
                    AudienceMember.version == audience.active_membership_version
                )
            ).count()
            
            return count
        else:
            # All respondents in dataset
            count = db.query(Respondent).filter(
                Respondent.dataset_id == dataset_id
            ).count()
            return count
    
    def apply_negation_filter(
        self,
        query,
        negation_ast: Optional[Dict[str, Any]],
        value_code_column,
        value_label_table=None
    ):
        """
        Apply negation AST to query
        
        Args:
            query: SQLAlchemy query object
            negation_ast: Negation AST structure
            value_code_column: Column reference for value_code
        """
        if not negation_ast or negation_ast.get("type") == "NONE":
            return query
        
        ast_type = negation_ast.get("type")
        targets = negation_ast.get("targets", [])
        operator = negation_ast.get("operator")
        
        if ast_type == "NOT" and operator == "!=":
            if targets:
                # NOT IN targets
                query = query.filter(~value_code_column.in_(targets))
            # Otherwise, no filter (handled in aggregation logic)
        
        elif ast_type == "EXCEPT" and operator == "NOT_IN":
            if targets:
                query = query.filter(~value_code_column.in_(targets))
        
        elif ast_type == "LEAST" and operator == "MIN":
            # This will be handled post-aggregation (select min percent category)
            pass
        
        elif ast_type == "COMPARE":
            # Will handle in aggregation result processing
            pass
        
        return query
    
    def aggregate_single_choice(
        self,
        db: Session,
        variable_id: int,
        dataset_id: str,
        audience_id: Optional[str],
        negation_ast: Optional[Dict[str, Any]] = None,
        group_by_variable_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Aggregate single-choice variable
        
        Returns evidence_json with base_n, answered_n, response_rate, missing_n, categories
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        variable = db.query(Variable).filter(Variable.id == variable_id).first()
        if not variable:
            raise ValueError(f"Variable {variable_id} not found")
        
        # Get base_n
        base_n = self.get_base_n(db, audience_id, dataset_id)
        
        # Build aggregation query with audience filter
        if audience_id:
            # Join with audience_members (active version)
            # For single-choice, count DISTINCT respondent_id to avoid duplicate counting
            query = db.query(
                Response.value_code,
                ValueLabel.value_label,
                func.count(func.distinct(Response.respondent_id)).label('count')
            ).join(
                Respondent,
                Response.respondent_id == Respondent.id
            ).join(
                AudienceMember,
                Response.respondent_id == AudienceMember.respondent_id
            ).join(
                Audience,
                AudienceMember.audience_id == Audience.id
            ).join(
                ValueLabel,
                and_(
                    Response.variable_id == ValueLabel.variable_id,
                    self._build_value_label_join_condition(Response.value_code, ValueLabel)
                ),
                isouter=True
            ).filter(
                Response.variable_id == variable_id,
                Response.is_missing == False,
                Respondent.dataset_id == dataset_id,
                Audience.id == audience_id,
                AudienceMember.version == Audience.active_membership_version
            )
        else:
            # No audience filter
            # Join with Respondent to ensure dataset_id match
            # For single-choice, count DISTINCT respondent_id to avoid duplicate counting
            query = db.query(
                Response.value_code,
                ValueLabel.value_label,
                func.count(func.distinct(Response.respondent_id)).label('count')
            ).join(
                Respondent,
                Response.respondent_id == Respondent.id
            ).join(
                ValueLabel,
                and_(
                    Response.variable_id == ValueLabel.variable_id,
                    self._build_value_label_join_condition(Response.value_code, ValueLabel)
                ),
                isouter=True
            ).filter(
                Response.variable_id == variable_id,
                Response.is_missing == False,
                Respondent.dataset_id == dataset_id
            )
        
        # Apply negation filter
        query = self.apply_negation_filter(query, negation_ast, Response.value_code)
        
        # Group by value_code
        query = query.group_by(Response.value_code, ValueLabel.value_label)
        
        # Execute query
        results = query.all()
        
        # Calculate answered_n (sum of counts) - this is now distinct respondent counts per category
        answered_n = sum(row.count for row in results)
        missing_n = base_n - answered_n
        response_rate = answered_n / base_n if base_n > 0 else 0.0
        
        # Build categories and track missing labels
        categories = []
        missing_label_codes = []
        
        for row in results:
            percent = (row.count / answered_n * 100) if answered_n > 0 else 0.0
            value_code_str = str(row.value_code) if row.value_code else None
            
            # Check if label was found
            label = row.value_label
            if not label:
                label = str(row.value_code) or "Unknown"
                if value_code_str and value_code_str != "Unknown":
                    missing_label_codes.append(value_code_str)
            
            categories.append({
                "value_code": value_code_str,
                "label": label,
                "count": row.count,
                "percent": round(percent, 2)
            })
        
        # Sort by count descending
        categories.sort(key=lambda x: x['count'], reverse=True)
        
        # Handle negation LEAST - select minimum percent category
        if negation_ast and negation_ast.get("type") == "LEAST":
            if categories:
                min_category = min(categories, key=lambda x: x['percent'])
                categories = [min_category]
        
        # Build evidence_json
        evidence_json = {
            "question_text": variable.question_text or variable.label or variable.code,
            "variable_code": variable.code,
            "base_n": base_n,
            "answered_n": answered_n,
            "response_rate": round(response_rate, 4),
            "missing_n": missing_n,
            "categories": categories
        }
        
        # Add warnings if labels are missing
        if missing_label_codes:
            evidence_json["warnings"] = {
                "missing_label_codes": list(set(missing_label_codes))  # Deduplicate
            }
        
        return evidence_json
    
    def aggregate_numeric(
        self,
        db: Session,
        variable_id: int,
        dataset_id: str,
        audience_id: Optional[str],
        negation_ast: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate numeric variable
        
        Returns evidence_json with base_n, answered_n, response_rate, missing_n, stats (min, max, mean, median)
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        variable = db.query(Variable).filter(Variable.id == variable_id).first()
        if not variable:
            raise ValueError(f"Variable {variable_id} not found")
        
        # Get base_n
        base_n = self.get_base_n(db, audience_id, dataset_id)
        
        # Build aggregation query
        if audience_id:
            query = db.query(
                func.min(Response.numeric_value).label('min_val'),
                func.max(Response.numeric_value).label('max_val'),
                func.avg(Response.numeric_value).label('mean_val'),
                func.count(Response.id).label('count')
            ).join(
                AudienceMember,
                Response.respondent_id == AudienceMember.respondent_id
            ).join(
                Audience,
                AudienceMember.audience_id == Audience.id
            ).filter(
                Response.variable_id == variable_id,
                Response.is_missing == False,
                Response.numeric_value.isnot(None),
                Audience.id == audience_id,
                AudienceMember.version == Audience.active_membership_version
            )
        else:
            query = db.query(
                func.min(Response.numeric_value).label('min_val'),
                func.max(Response.numeric_value).label('max_val'),
                func.avg(Response.numeric_value).label('mean_val'),
                func.count(Response.id).label('count')
            ).filter(
                Response.variable_id == variable_id,
                Response.is_missing == False,
                Response.numeric_value.isnot(None)
            )
        
        result = query.first()
        
        if not result or result.count == 0:
            answered_n = 0
            missing_n = base_n
            stats = {}
        else:
            answered_n = result.count
            missing_n = base_n - answered_n
            
            # Calculate median (requires separate query or post-processing)
            # For now, use mean as approximation
            stats = {
                "min": float(result.min_val) if result.min_val is not None else None,
                "max": float(result.max_val) if result.max_val is not None else None,
                "mean": float(result.mean_val) if result.mean_val is not None else None,
                "median": None  # TODO: Calculate median
            }
        
        response_rate = answered_n / base_n if base_n > 0 else 0.0
        
        evidence_json = {
            "question_text": variable.question_text or variable.label or variable.code,
            "variable_code": variable.code,
            "base_n": base_n,
            "answered_n": answered_n,
            "response_rate": round(response_rate, 4),
            "missing_n": missing_n,
            "stats": stats
        }
        
        return evidence_json
    
    def aggregate_with_breakdown(
        self,
        db: Session,
        variable_id: int,
        group_by_variable_id: int,
        dataset_id: str,
        audience_id: Optional[str],
        negation_ast: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate with breakdown (2D aggregation)
        Example: "age by region"
        
        Uses self-join to combine responses from two variables for the same respondent.
        
        Returns evidence_json with cells array containing row/col combinations.
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        primary_var = db.query(Variable).filter(Variable.id == variable_id).first()
        group_by_var = db.query(Variable).filter(Variable.id == group_by_variable_id).first()
        
        if not primary_var or not group_by_var:
            raise ValueError("Variable not found")
        
        # Get base_n
        base_n = self.get_base_n(db, audience_id, dataset_id)
        
        # Build 2D aggregation query using self-join
        # Use raw SQL approach for simplicity with aliases
        # We'll build a query that joins Response table twice (r1 for primary, r2 for group_by)
        
        # Get ValueLabels for both variables (for label lookup)
        vl1_dict = {}  # {value_code: label} for primary variable
        vl2_dict = {}  # {value_code: label} for group_by variable
        
        for vl in db.query(ValueLabel).filter(ValueLabel.variable_id == variable_id).all():
            vl1_dict[vl.value_code] = vl.value_label
        
        for vl in db.query(ValueLabel).filter(ValueLabel.variable_id == group_by_variable_id).all():
            vl2_dict[vl.value_code] = vl.value_label
        
        # Build query: join Response twice on respondent_id
        # r1 = responses for primary variable
        # r2 = responses for group_by variable
        
        # Use subquery approach or explicit join
        base_query = db.query(
            Response.value_code.label('row_value_code'),
            Response.respondent_id.label('respondent_id')
        ).filter(
            Response.variable_id == variable_id,
            Response.is_missing == False
        ).subquery(name='r1')
        
        r2_subq = db.query(
            Response.value_code.label('col_value_code'),
            Response.respondent_id.label('respondent_id')
        ).filter(
            Response.variable_id == group_by_variable_id,
            Response.is_missing == False
        ).subquery(name='r2')
        
        # Join on respondent_id and group by both value codes
        query = db.query(
            base_query.c.row_value_code,
            r2_subq.c.col_value_code,
            func.count(func.distinct(base_query.c.respondent_id)).label('count')
        ).join(
            r2_subq,
            base_query.c.respondent_id == r2_subq.c.respondent_id
        ).join(
            Respondent,
            base_query.c.respondent_id == Respondent.id
        ).filter(
            Respondent.dataset_id == dataset_id
        )
        
        # Apply audience filter if provided
        if audience_id:
            query = query.join(
                AudienceMember,
                base_query.c.respondent_id == AudienceMember.respondent_id
            ).join(
                Audience,
                AudienceMember.audience_id == Audience.id
            ).filter(
                Audience.id == audience_id,
                AudienceMember.version == Audience.active_membership_version
            )
        
        # Apply negation filter to primary variable
        if negation_ast and negation_ast.get("type") != "NONE":
            targets = negation_ast.get("targets", [])
            if targets:
                query = query.filter(~base_query.c.row_value_code.in_(targets))
        
        # Group by both value codes
        query = query.group_by(
            base_query.c.row_value_code,
            r2_subq.c.col_value_code
        )
        
        # Execute query
        results = query.all()
        
        # Build cells array
        cells = []
        total_valid = 0
        
        for row in results:
            count = row.count
            total_valid += count
            
            row_code = str(row.row_value_code) if row.row_value_code else None
            col_code = str(row.col_value_code) if row.col_value_code else None
            
            # Get labels from dictionaries
            row_label = vl1_dict.get(row_code, row_code) if row_code else "Unknown"
            col_label = vl2_dict.get(col_code, col_code) if col_code else "Unknown"
            
            cells.append({
                "row_value_code": row_code,
                "row_label": row_label,
                "col_value_code": col_code,
                "col_label": col_label,
                "count": count
            })
        
        # Calculate row and column totals for percentages
        row_totals = {}  # {row_value_code: total_count}
        col_totals = {}  # {col_value_code: total_count}
        
        for cell in cells:
            row_code = cell["row_value_code"]
            col_code = cell["col_value_code"]
            
            if row_code:
                row_totals[row_code] = row_totals.get(row_code, 0) + cell["count"]
            if col_code:
                col_totals[col_code] = col_totals.get(col_code, 0) + cell["count"]
        
        # Add percentages to cells
        for cell in cells:
            row_code = cell["row_value_code"]
            col_code = cell["col_value_code"]
            count = cell["count"]
            
            # Percent of row valid
            if row_code and row_totals.get(row_code, 0) > 0:
                cell["percent_of_row_valid"] = round((count / row_totals[row_code]) * 100, 2)
            else:
                cell["percent_of_row_valid"] = 0.0
            
            # Percent of col valid
            if col_code and col_totals.get(col_code, 0) > 0:
                cell["percent_of_col_valid"] = round((count / col_totals[col_code]) * 100, 2)
            else:
                cell["percent_of_col_valid"] = 0.0
        
        # Sort cells by count descending
        cells.sort(key=lambda x: x['count'], reverse=True)
        
        answered_n = total_valid
        missing_n = base_n - answered_n
        response_rate = answered_n / base_n if base_n > 0 else 0.0
        
        # Build evidence_json
        evidence_json = {
            "question_text": f"{primary_var.question_text or primary_var.code} by {group_by_var.question_text or group_by_var.code}",
            "primary_variable_code": primary_var.code,
            "group_by_variable_code": group_by_var.code,
            "base_n": base_n,
            "answered_n": answered_n,
            "response_rate": round(response_rate, 4),
            "missing_n": missing_n,
            "cells": cells
        }
        
        return evidence_json
    
    def compare_audience_vs_total(
        self,
        db: Session,
        variable_id: int,
        audience_id: str,
        dataset_id: str,
        negation_ast: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare audience aggregation with total sample aggregation.
        
        Makes two separate aggregation calls:
        - Audience segment: with audience_id
        - Total sample: with audience_id=None
        
        Returns combined evidence_json with comparison_type="audience_vs_total".
        
        Args:
            db: Database session
            variable_id: Primary variable ID
            audience_id: Audience ID to compare
            dataset_id: Dataset ID
            negation_ast: Optional negation AST
            
        Returns:
            Dict with comparison_type, audience, and total evidence_json structures
        """
        # Get audience aggregation
        audience_evidence = self.aggregate_single_choice(
            db=db,
            variable_id=variable_id,
            dataset_id=dataset_id,
            audience_id=audience_id,
            negation_ast=negation_ast
        )
        
        # Get total sample aggregation
        total_evidence = self.aggregate_single_choice(
            db=db,
            variable_id=variable_id,
            dataset_id=dataset_id,
            audience_id=None,  # Total sample
            negation_ast=negation_ast
        )
        
        # Build comparison evidence_json
        comparison_evidence = {
            "comparison_type": "audience_vs_total",
            "primary_variable_code": audience_evidence.get("variable_code"),
            "audience_id": audience_id,
            "audience": audience_evidence,
            "total": total_evidence
        }
        
        return comparison_evidence
    
    def generate_chart_json(
        self,
        evidence_json: Dict[str, Any],
        variable_type: str
    ) -> Dict[str, Any]:
        """
        Generate chart JSON from evidence_json
        
        Returns chart data suitable for Chart.js or similar
        
        Supports:
        - Regular evidence_json (with categories)
        - Comparison evidence_json (with comparison_type="audience_vs_total")
        - Breakdown evidence_json (with cells array)
        """
        # Handle breakdown evidence_json (2D aggregation - X by Y)
        if 'cells' in evidence_json and evidence_json.get('cells'):
            cells = evidence_json.get('cells', [])
            
            # Get unique row and column labels
            row_labels = []
            col_labels = []
            cell_data = {}  # {(row_label, col_label): count}
            
            for cell in cells:
                row_label = cell.get('row_label', 'Unknown')
                col_label = cell.get('col_label', 'Unknown')
                
                if row_label not in row_labels:
                    row_labels.append(row_label)
                if col_label not in col_labels:
                    col_labels.append(col_label)
                
                cell_data[(row_label, col_label)] = cell.get('count', 0)
            
            # Build datasets for grouped bar chart (one dataset per column/category)
            datasets = []
            colors = [
                'rgba(54, 162, 235, 0.6)',   # Blue
                'rgba(255, 99, 132, 0.6)',   # Red
                'rgba(75, 192, 192, 0.6)',   # Teal
                'rgba(255, 206, 86, 0.6)',   # Yellow
                'rgba(153, 102, 255, 0.6)',  # Purple
                'rgba(255, 159, 64, 0.6)',   # Orange
            ]
            
            for i, col_label in enumerate(col_labels):
                data = [cell_data.get((row_label, col_label), 0) for row_label in row_labels]
                datasets.append({
                    "label": col_label,
                    "data": data,
                    "backgroundColor": colors[i % len(colors)],
                    "borderColor": colors[i % len(colors)].replace('0.6', '1'),
                    "borderWidth": 1
                })
            
            return {
                "type": "bar",
                "data": {
                    "labels": row_labels,
                    "datasets": datasets
                },
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": True,
                            "title": {
                                "display": True,
                                "text": "Count"
                            }
                        },
                        "x": {
                            "title": {
                                "display": True,
                                "text": evidence_json.get('primary_variable_code', 'Primary Variable')
                            }
                        }
                    },
                    "plugins": {
                        "legend": {
                            "display": True,
                            "position": "top"
                        }
                    }
                }
            }
        
        # Handle comparison evidence_json
        if evidence_json.get('comparison_type') == 'audience_vs_total':
            audience_evidence = evidence_json.get('audience', {})
            total_evidence = evidence_json.get('total', {})
            
            audience_categories = audience_evidence.get('categories', [])
            total_categories = total_evidence.get('categories', [])
            
            # Get all unique labels (union of audience and total categories)
            all_labels = []
            label_to_audience_pct = {}
            label_to_total_pct = {}
            
            for cat in audience_categories:
                label = cat.get('label', 'Unknown')
                if label not in all_labels:
                    all_labels.append(label)
                label_to_audience_pct[label] = cat.get('percent', 0)
            
            for cat in total_categories:
                label = cat.get('label', 'Unknown')
                if label not in all_labels:
                    all_labels.append(label)
                label_to_total_pct[label] = cat.get('percent', 0)
            
            # Build datasets for comparison chart
            audience_data = [label_to_audience_pct.get(label, 0) for label in all_labels]
            total_data = [label_to_total_pct.get(label, 0) for label in all_labels]
            
            return {
                "type": "bar",
                "data": {
                    "labels": all_labels,
                    "datasets": [
                        {
                            "label": "Audience",
                            "data": audience_data,
                            "backgroundColor": "rgba(54, 162, 235, 0.6)",
                            "borderColor": "rgba(54, 162, 235, 1)",
                            "borderWidth": 1
                        },
                        {
                            "label": "Total Sample",
                            "data": total_data,
                            "backgroundColor": "rgba(255, 99, 132, 0.6)",
                            "borderColor": "rgba(255, 99, 132, 1)",
                            "borderWidth": 1
                        }
                    ]
                },
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": True,
                            "title": {
                                "display": True,
                                "text": "Percentage (%)"
                            }
                        },
                        "x": {
                            "title": {
                                "display": True,
                                "text": "Category"
                            }
                        }
                    },
                    "plugins": {
                        "legend": {
                            "display": True,
                            "position": "top"
                        }
                    }
                }
            }
        
        # Regular evidence_json (non-comparison)
        if variable_type in ['single_choice', 'multi_choice']:
            categories = evidence_json.get('categories', [])
            
            return {
                "type": "bar",  # or "pie" depending on preference
                "data": {
                    "labels": [cat['label'] for cat in categories],
                    "datasets": [{
                        "label": "Count",
                        "data": [cat['count'] for cat in categories]
                    }]
                },
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": True
                        }
                    }
                }
            }
        elif variable_type == 'numeric':
            stats = evidence_json.get('stats', {})
            # Histogram or box plot
            return {
                "type": "bar",
                "data": {
                    "labels": ["Min", "Max", "Mean"],
                    "datasets": [{
                        "label": "Value",
                        "data": [stats.get('min'), stats.get('max'), stats.get('mean')]
                    }]
                }
            }
        else:
            return {"type": "unknown", "data": {}}


# Singleton instance
structured_aggregation_service = StructuredAggregationService()

