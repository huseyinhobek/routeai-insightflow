"""
Data Quality Analyzer Service
Analyzes SAV datasets for data quality, completeness, and digital twin readiness
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class QualityLevel(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class QualityMetric:
    name: str
    score: float
    status: str
    details: str
    recommendations: List[str]


@dataclass
class VariableQuality:
    code: str
    label: str
    completeness: float
    validity: float
    consistency: float
    overall_status: str
    issues: List[str]


@dataclass
class QualityReport:
    """Comprehensive data quality report"""
    # Overall scores
    overall_score: float
    completeness_score: float
    validity_score: float
    consistency_score: float
    digital_twin_readiness: str
    
    # Participant stats
    total_participants: int
    complete_responses: int
    partial_responses: int
    dropout_rate: float
    
    # Variable quality
    total_variables: int
    high_quality_vars: int
    medium_quality_vars: int
    low_quality_vars: int
    
    # Detailed metrics
    metrics: List[Dict]
    variable_quality: List[Dict]
    
    # Recommendations
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    # Transformation readiness
    transformation_score: float
    transformation_issues: List[str]


class QualityAnalyzer:
    """Analyzes data quality for digital twin readiness"""
    
    def __init__(self, df: pd.DataFrame, meta: Any, variables_info: List[Dict]):
        self.df = df
        self.meta = meta
        self.variables_info = variables_info
        
    def analyze(self) -> QualityReport:
        """Run comprehensive quality analysis"""
        
        # Calculate core metrics
        completeness = self._analyze_completeness()
        validity = self._analyze_validity()
        consistency = self._analyze_consistency()
        variable_quality = self._analyze_variable_quality()
        transformation = self._analyze_transformation_readiness()
        
        # Calculate overall score
        overall_score = (
            completeness["score"] * 0.4 +
            validity["score"] * 0.3 +
            consistency["score"] * 0.3
        )
        
        # Determine digital twin readiness
        if overall_score >= 80 and transformation["score"] >= 70:
            readiness = QualityLevel.GREEN.value
        elif overall_score >= 60 and transformation["score"] >= 50:
            readiness = QualityLevel.YELLOW.value
        else:
            readiness = QualityLevel.RED.value
        
        # Compile recommendations
        recommendations = self._generate_recommendations(
            completeness, validity, consistency, transformation
        )
        
        return QualityReport(
            overall_score=round(overall_score, 1),
            completeness_score=round(completeness["score"], 1),
            validity_score=round(validity["score"], 1),
            consistency_score=round(consistency["score"], 1),
            digital_twin_readiness=readiness,
            
            total_participants=len(self.df),
            complete_responses=completeness["complete_responses"],
            partial_responses=completeness["partial_responses"],
            dropout_rate=round(completeness["dropout_rate"], 2),
            
            total_variables=len(self.df.columns),
            high_quality_vars=sum(1 for v in variable_quality if v["status"] == "green"),
            medium_quality_vars=sum(1 for v in variable_quality if v["status"] == "yellow"),
            low_quality_vars=sum(1 for v in variable_quality if v["status"] == "red"),
            
            metrics=[
                {"name": "Completeness", "score": completeness["score"], "status": completeness["status"]},
                {"name": "Validity", "score": validity["score"], "status": validity["status"]},
                {"name": "Consistency", "score": consistency["score"], "status": consistency["status"]},
                {"name": "Transformation", "score": transformation["score"], "status": transformation["status"]},
            ],
            variable_quality=variable_quality,
            
            critical_issues=recommendations["critical"],
            warnings=recommendations["warnings"],
            recommendations=recommendations["suggestions"],
            
            transformation_score=round(transformation["score"], 1),
            transformation_issues=transformation["issues"]
        )
    
    def _analyze_completeness(self) -> Dict[str, Any]:
        """Analyze data completeness"""
        total_cells = self.df.size
        missing_cells = self.df.isna().sum().sum()
        completeness_rate = ((total_cells - missing_cells) / total_cells) * 100
        
        # Per-row completeness
        row_completeness = self.df.notna().sum(axis=1) / len(self.df.columns) * 100
        complete_responses = (row_completeness >= 90).sum()
        partial_responses = ((row_completeness >= 50) & (row_completeness < 90)).sum()
        dropout_rate = (row_completeness < 50).sum() / len(self.df) * 100
        
        # Status
        if completeness_rate >= 85:
            status = "green"
        elif completeness_rate >= 70:
            status = "yellow"
        else:
            status = "red"
        
        return {
            "score": completeness_rate,
            "status": status,
            "complete_responses": int(complete_responses),
            "partial_responses": int(partial_responses),
            "dropout_rate": dropout_rate
        }
    
    def _analyze_validity(self) -> Dict[str, Any]:
        """Analyze data validity (values within expected ranges)"""
        valid_scores = []
        
        for var_info in self.variables_info:
            col = var_info["code"]
            if col not in self.df.columns:
                continue
                
            series = self.df[col].dropna()
            if len(series) == 0:
                continue
            
            # Check if values match value labels
            if var_info.get("valueLabels"):
                valid_values = set(vl["value"] for vl in var_info["valueLabels"])
                if valid_values:
                    valid_count = series.isin(valid_values).sum()
                    valid_scores.append(valid_count / len(series) * 100)
            else:
                # Numeric: check for outliers using IQR
                if pd.api.types.is_numeric_dtype(series):
                    q1, q3 = series.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    lower = q1 - 3 * iqr
                    upper = q3 + 3 * iqr
                    valid_count = ((series >= lower) & (series <= upper)).sum()
                    valid_scores.append(valid_count / len(series) * 100)
        
        avg_validity = np.mean(valid_scores) if valid_scores else 100
        
        if avg_validity >= 95:
            status = "green"
        elif avg_validity >= 85:
            status = "yellow"
        else:
            status = "red"
        
        return {"score": avg_validity, "status": status}
    
    def _analyze_consistency(self) -> Dict[str, Any]:
        """Analyze data consistency (patterns, logical checks)"""
        consistency_scores = []
        
        # Check for duplicate rows
        duplicate_rate = self.df.duplicated().sum() / len(self.df) * 100
        consistency_scores.append(100 - duplicate_rate)
        
        # Check for monotonic response patterns (straight-lining)
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 5:
            # Detect rows with zero variance (all same answers)
            row_variance = self.df[numeric_cols].var(axis=1)
            straight_line_rate = (row_variance == 0).sum() / len(self.df) * 100
            consistency_scores.append(100 - straight_line_rate)
        
        avg_consistency = np.mean(consistency_scores)
        
        if avg_consistency >= 95:
            status = "green"
        elif avg_consistency >= 85:
            status = "yellow"
        else:
            status = "red"
        
        return {"score": avg_consistency, "status": status}
    
    def _analyze_variable_quality(self) -> List[Dict]:
        """Analyze quality of each variable"""
        results = []
        
        for var_info in self.variables_info:
            col = var_info["code"]
            if col not in self.df.columns:
                continue
            
            series = self.df[col]
            
            # Completeness
            completeness = series.notna().sum() / len(series) * 100
            
            # Issues
            issues = []
            if completeness < 50:
                issues.append("Very high missing rate (>50%)")
            elif completeness < 80:
                issues.append("High missing rate (>20%)")
            
            # Low cardinality check
            if var_info.get("cardinality", 0) == 1:
                issues.append("Zero variance (only one unique value)")
            
            # Determine status
            if completeness >= 90 and len(issues) == 0:
                status = "green"
            elif completeness >= 70 and len(issues) <= 1:
                status = "yellow"
            else:
                status = "red"
            
            results.append({
                "code": col,
                "label": var_info.get("label", col),
                "completeness": round(completeness, 1),
                "status": status,
                "issues": issues
            })
        
        return results
    
    def _analyze_transformation_readiness(self) -> Dict[str, Any]:
        """Analyze readiness for digital twin transformation"""
        issues = []
        scores = []
        
        # Check for minimum sample size
        if len(self.df) < 100:
            issues.append("Sample size too small (<100) for reliable transformation")
            scores.append(50)
        elif len(self.df) < 500:
            issues.append("Sample size is marginal (100-500), results may have limited generalizability")
            scores.append(75)
        else:
            scores.append(100)
        
        # Check for key demographic variables
        demo_keywords = ['age', 'gender', 'sex', 'region', 'income', 'education', 'yas', 'cinsiyet']
        has_demographics = any(
            any(kw in v.get("code", "").lower() or kw in v.get("label", "").lower() 
                for kw in demo_keywords)
            for v in self.variables_info
        )
        if not has_demographics:
            issues.append("No demographic variables detected for segmentation")
            scores.append(60)
        else:
            scores.append(100)
        
        # Check overall completeness
        overall_completeness = self.df.notna().sum().sum() / self.df.size * 100
        if overall_completeness < 70:
            issues.append("Overall data completeness below 70%")
            scores.append(overall_completeness)
        else:
            scores.append(100)
        
        avg_score = np.mean(scores)
        
        if avg_score >= 85:
            status = "green"
        elif avg_score >= 65:
            status = "yellow"
        else:
            status = "red"
        
        return {"score": avg_score, "status": status, "issues": issues}
    
    def _generate_recommendations(self, completeness: Dict, validity: Dict, 
                                   consistency: Dict, transformation: Dict) -> Dict[str, List[str]]:
        """Generate actionable recommendations"""
        critical = []
        warnings = []
        suggestions = []
        
        # Critical issues
        if completeness["score"] < 60:
            critical.append("Data completeness is critically low. Consider data imputation or re-collection.")
        
        if validity["score"] < 80:
            critical.append("Data validity issues detected. Review out-of-range values.")
        
        if transformation["score"] < 60:
            critical.append("Data is NOT ready for digital twin transformation without significant preprocessing.")
        
        # Warnings
        if completeness["dropout_rate"] > 20:
            warnings.append(f"High dropout rate ({completeness['dropout_rate']:.1f}%). Consider survey redesign.")
        
        if consistency["score"] < 90:
            warnings.append("Potential straight-lining detected. Review response patterns.")
        
        # Suggestions
        if completeness["score"] < 85:
            suggestions.append("Consider implementing progressive disclosure in surveys to reduce abandonment.")
        
        if len(self.df.columns) > 100:
            suggestions.append("Large number of variables detected. Consider dimensionality reduction.")
        
        suggestions.append("Export detailed variable quality report for variable-level cleanup.")
        
        return {
            "critical": critical,
            "warnings": warnings,
            "suggestions": suggestions
        }

