"""
Unit tests for variable statistics computation with correct missing handling
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from main import (
    is_value_missing,
    get_explicit_missing_codes,
    compute_variable_stats
)


class TestIsMissingValue:
    """Test implicit missing detection"""
    
    def test_nan_is_missing(self):
        assert is_value_missing(np.nan) is True
        assert is_value_missing(pd.NA) is True
        assert is_value_missing(None) is True
    
    def test_empty_string_is_missing(self):
        assert is_value_missing("") is True
        assert is_value_missing("   ") is True
        assert is_value_missing("\t\n") is True
    
    def test_valid_values_not_missing(self):
        assert is_value_missing(0) is False
        assert is_value_missing("hello") is False
        assert is_value_missing(123) is False
        assert is_value_missing("0") is False


class TestExplicitMissingCodes:
    """Test explicit missing code detection"""
    
    def test_user_missing_values(self):
        var_info = {
            "code": "Q1",
            "missingValues": {
                "systemMissing": True,
                "userMissingValues": [99, 98]
            }
        }
        meta = None
        
        codes = get_explicit_missing_codes(var_info, meta)
        assert 99 in codes
        assert 98 in codes
    
    def test_non_substantive_labels(self):
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Yes"},
                {"value": 2, "label": "No"},
                {"value": 99, "label": "Don't know"},
                {"value": 98, "label": "Refused"}
            ]
        }
        meta = None
        
        codes = get_explicit_missing_codes(var_info, meta)
        assert 99 in codes
        assert 98 in codes
        assert 1 not in codes
        assert 2 not in codes
    
    def test_no_missing_codes(self):
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Yes"},
                {"value": 2, "label": "No"}
            ]
        }
        meta = None
        
        codes = get_explicit_missing_codes(var_info, meta)
        assert len(codes) == 0


class TestComputeVariableStats:
    """Test comprehensive variable statistics computation"""
    
    def test_only_blanks(self):
        """Case: only implicit missing (blanks)"""
        df = pd.DataFrame({
            "Q1": [1, 2, 3, np.nan, np.nan, "", "  ", 1, 2]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Option 1"},
                {"value": 2, "label": "Option 2"},
                {"value": 3, "label": "Option 3"}
            ]
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["totalN"] == 9
        assert result["validN"] == 5  # 1,2,3,1,2
        assert result["missingN"] == 4  # nan, nan, "", "  "
        assert result["missingPercentOfTotal"] == round(4/9*100, 2)
        
        # Check frequencies
        freq_dict = {f["value"]: f["count"] for f in result["frequencies"] if f["value"] is not None}
        assert freq_dict.get(1) == 2
        assert freq_dict.get(2) == 2
        assert freq_dict.get(3) == 1
        
        # Check missing row
        missing_row = next((f for f in result["frequencies"] if f["value"] is None), None)
        assert missing_row is not None
        assert missing_row["count"] == 4
        assert missing_row["label"] == "Missing / No answer"
    
    def test_explicit_missing_codes(self):
        """Case: explicit missing codes present"""
        df = pd.DataFrame({
            "Q1": [1, 2, 3, 99, 98, 1, 2, 99, 1]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Yes"},
                {"value": 2, "label": "No"},
                {"value": 3, "label": "Maybe"},
                {"value": 99, "label": "Don't know"},
                {"value": 98, "label": "Refused"}
            ],
            "missingValues": {
                "systemMissing": True,
                "userMissingValues": [99, 98]
            }
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["totalN"] == 9
        assert result["validN"] == 6  # 1,2,3,1,2,1
        assert result["missingN"] == 3  # 99, 98, 99
        
        # Check that 99 and 98 are NOT in valid frequencies
        freq_dict = {f["value"]: f["count"] for f in result["frequencies"] if f["value"] is not None}
        assert 99 not in freq_dict
        assert 98 not in freq_dict
        assert freq_dict.get(1) == 3
        assert freq_dict.get(2) == 2
        assert freq_dict.get(3) == 1
    
    def test_both_blanks_and_explicit_missing(self):
        """Case: both blanks and explicit missing codes"""
        df = pd.DataFrame({
            "Q1": [1, 2, np.nan, 99, "", 1, 2, 98, 1, "  "]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Yes"},
                {"value": 2, "label": "No"},
                {"value": 99, "label": "Don't know"},
                {"value": 98, "label": "Refused"}
            ],
            "missingValues": {
                "systemMissing": True,
                "userMissingValues": [99, 98]
            }
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["totalN"] == 10
        assert result["validN"] == 5  # 1,2,1,2,1
        assert result["missingN"] == 5  # nan, 99, "", 98, "  "
        assert result["missingPercentOfTotal"] == 50.0
    
    def test_percentages_calculation(self):
        """Test that percentOfTotal and percentOfValid are correctly calculated"""
        df = pd.DataFrame({
            "Q1": [1, 1, 2, np.nan, np.nan]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": [
                {"value": 1, "label": "Yes"},
                {"value": 2, "label": "No"}
            ]
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["totalN"] == 5
        assert result["validN"] == 3
        assert result["missingN"] == 2
        
        # Find frequency for value 1
        freq_1 = next(f for f in result["frequencies"] if f["value"] == 1)
        assert freq_1["count"] == 2
        assert freq_1["percentOfTotal"] == 40.0  # 2/5
        assert freq_1["percentOfValid"] == round(2/3*100, 2)  # 2/3
        
        # Find frequency for value 2
        freq_2 = next(f for f in result["frequencies"] if f["value"] == 2)
        assert freq_2["count"] == 1
        assert freq_2["percentOfTotal"] == 20.0  # 1/5
        assert freq_2["percentOfValid"] == round(1/3*100, 2)  # 1/3
        
        # Find missing row
        missing_row = next(f for f in result["frequencies"] if f["value"] is None)
        assert missing_row["count"] == 2
        assert missing_row["percentOfTotal"] == 40.0  # 2/5
        assert missing_row["percentOfValid"] == 0.0  # Not part of valid
    
    def test_high_cardinality_detection(self):
        """Test hasManyCategories flag for high cardinality variables"""
        # Create a variable with 15 unique values
        df = pd.DataFrame({
            "Q1": list(range(1, 16)) + [np.nan]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": []
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["categoryCount"] == 15
        assert result["hasManyCategories"] is True
    
    def test_low_cardinality(self):
        """Test hasManyCategories flag for low cardinality variables"""
        df = pd.DataFrame({
            "Q1": [1, 2, 3, 1, 2, 3, np.nan]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": []
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["categoryCount"] == 3
        assert result["hasManyCategories"] is False
    
    def test_total_n_consistency(self):
        """Test that totalN equals validN + missingN"""
        df = pd.DataFrame({
            "Q1": [1, 2, 3, np.nan, 99, "", 1, 2]
        })
        
        var_info = {
            "code": "Q1",
            "valueLabels": [],
            "missingValues": {
                "userMissingValues": [99]
            }
        }
        meta = None
        
        result = compute_variable_stats(df, "Q1", var_info, meta)
        
        assert result["totalN"] == result["validN"] + result["missingN"]
        assert result["totalN"] == len(df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

