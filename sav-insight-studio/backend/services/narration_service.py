"""
Narration service for LLM-generated narratives with guardrails
"""
from typing import Dict, Any, Optional, List
import re
import logging

logger = logging.getLogger(__name__)


class NarrationService:
    """Service for generating narratives with strict guardrails"""
    
    def __init__(self):
        # Quantifier policy thresholds
        self.quantifier_policy = {
            "majority": 0.50,
            "overwhelming majority": 0.75,
            "nearly all": 0.90,
            "vast majority": 0.75,
            "minority": 0.50,
            "tiny minority": 0.10,
            "few": 0.25
        }
    
    def validate_numbers(
        self,
        narrative_text: str,
        evidence_json: Dict[str, Any]
    ) -> List[str]:
        """
        Validate that all numbers in narrative exist in evidence_json
        Uses tolerance for percentages to handle rounding (e.g., 95.83 ≈ 96)
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        TOLERANCE = 1.0  # Allow ±1.0 for percentages (handles rounding like 95.83 → 96)
        
        # Extract numbers from narrative
        # We'll validate all numbers but be lenient about numbers that might be from label text
        numbers = re.findall(r'\d+\.?\d*', narrative_text)
        if not numbers:
            return errors  # No numbers to validate
        
        # Build set of valid numbers from evidence (as floats for comparison)
        valid_numbers = []
        valid_percents = []
        valid_counts = []
        
        # From categories
        categories = evidence_json.get('categories', [])
        for cat in categories:
            count = cat.get('count', 0)
            percent = cat.get('percent', 0)
            if count is not None:
                valid_counts.append(float(count))
                valid_numbers.append(float(count))
            if percent is not None:
                valid_percents.append(float(percent))
                valid_numbers.append(float(percent))
        
        # From stats
        stats = evidence_json.get('stats', {})
        for key, value in stats.items():
            if value is not None:
                try:
                    valid_numbers.append(float(value))
                except (ValueError, TypeError):
                    pass
        
        # Check base_n, answered_n, etc.
        for key in ['base_n', 'answered_n', 'missing_n']:
            value = evidence_json.get(key, 0)
            if value is not None:
                try:
                    valid_counts.append(float(value))
                    valid_numbers.append(float(value))
                except (ValueError, TypeError):
                    pass
        
        # response_rate is already a percentage (0.0-1.0 or 0-100)
        response_rate = evidence_json.get('response_rate', 0.0)
        if response_rate is not None:
            try:
                rr_float = float(response_rate)
                # Convert to 0-100 scale if it's 0-1 scale
                if rr_float <= 1.0:
                    rr_float = rr_float * 100
                valid_percents.append(rr_float)
                valid_numbers.append(rr_float)
            except (ValueError, TypeError):
                pass
        
        # Check each number in narrative
        for num_str in numbers:
            num_str = num_str.rstrip('.')
            if not num_str:
                continue
            
            try:
                num_float = float(num_str)
            except (ValueError, TypeError):
                continue
            
            # Check if exact match exists
            if num_float in valid_numbers:
                continue
            
            # Check if within tolerance for percentages
            matched = False
            for valid_percent in valid_percents:
                if abs(num_float - valid_percent) <= TOLERANCE:
                    matched = True
                    break
            
            # Check if exact match for counts (counts should be exact, no tolerance)
            if not matched:
                if num_float in valid_counts:
                    matched = True
            
            # Also check base_n, answered_n, missing_n (exact match for counts)
            if not matched:
                base_n = evidence_json.get('base_n', 0)
                answered_n = evidence_json.get('answered_n', 0)
                missing_n = evidence_json.get('missing_n', 0)
                if num_float == float(base_n) or num_float == float(answered_n) or num_float == float(missing_n):
                    matched = True
            
            if not matched:
                # Number not found - could be from label text (like "65-74" in "Females 65-74")
                # Check if it's a reasonable number that might be from label
                # If it's a large number (>100) or very small (<0.1), it's probably not a label artifact
                # For numbers 1-100, they might be from labels, so be more lenient
                
                # Only error if:
                # 1. It's a large number (>100) - unlikely to be from label
                # 2. It's a percentage-like number (0-100) but not close to any valid percent/count
                # 3. Difference from closest valid number is significant (>5.0 for percentages, exact match required for counts)
                
                closest = min(valid_numbers, key=lambda x: abs(x - num_float)) if valid_numbers else None
                min_diff = abs(num_float - closest) if closest is not None else float('inf')
                
                # Skip validation for numbers that are likely from labels (e.g., "65", "74" in "65-74")
                # These are typically in ranges and we can't validate them against evidence
                if num_float < 0 or num_float > 100:
                    # Out of typical label range, validate it
                    if min_diff > 5.0:  # Significant difference
                        errors.append(f"Number {num_str} not found in evidence (closest: {closest})")
                else:
                    # Number 0-100, might be from label or valid stat
                    # Only error if it's very far from any valid number
                    if min_diff > 5.0 and num_float not in valid_counts:
                        # Significant difference and not a count, likely an error
                        errors.append(f"Number {num_str} not found in evidence (closest: {closest})")
                    # Otherwise, silently allow (likely from label text or minor rounding)
        
        return errors

    def validate_structured_numbers(
        self,
        narrative_text: str,
        evidence_json: Dict[str, Any]
    ) -> List[str]:
        """
        Structured-mode specific numeric validation.
        Only validates:
          - Percentages that explicitly include a '%' sign (e.g. '95.8%')
          - 'X out of Y' patterns where X and Y are counts.

        Plain numbers that might come from labels (e.g. '65-74' age bands)
        are intentionally ignored to avoid false positives.
        
        Supports both regular evidence_json and comparison evidence_json (with comparison_type="audience_vs_total").
        """
        errors: List[str] = []
        if not narrative_text:
            return errors

        # Collect valid percentages and counts from evidence
        valid_counts: List[float] = []
        valid_percents: List[float] = []

        # Handle breakdown evidence_json (cells array)
        if 'cells' in evidence_json and evidence_json.get('cells'):
            cells = evidence_json.get('cells', [])
            for cell in cells:
                c = cell.get('count')
                # Breakdown cells have percent_of_row_valid and percent_of_col_valid
                p_row = cell.get('percent_of_row_valid')
                p_col = cell.get('percent_of_col_valid')
                if c is not None:
                    valid_counts.append(float(c))
                if p_row is not None:
                    valid_percents.append(float(p_row))
                if p_col is not None:
                    valid_percents.append(float(p_col))
            
            # Collect base_n, answered_n, missing_n
            for key in ["base_n", "answered_n", "missing_n"]:
                v = evidence_json.get(key)
                if v is not None:
                    try:
                        valid_counts.append(float(v))
                    except (TypeError, ValueError):
                        pass
        # Handle comparison evidence_json
        elif evidence_json.get("comparison_type") == "audience_vs_total":
            # For comparison, collect percentages/counts from both audience and total
            audience_evidence = evidence_json.get("audience", {})
            total_evidence = evidence_json.get("total", {})
            
            # Collect from audience categories
            audience_categories = audience_evidence.get("categories", [])
            for cat in audience_categories:
                c = cat.get("count")
                p = cat.get("percent")
                if c is not None:
                    valid_counts.append(float(c))
                if p is not None:
                    valid_percents.append(float(p))
            
            # Collect from total categories
            total_categories = total_evidence.get("categories", [])
            for cat in total_categories:
                c = cat.get("count")
                p = cat.get("percent")
                if c is not None:
                    valid_counts.append(float(c))
                if p is not None:
                    valid_percents.append(float(p))
            
            # Collect base_n, answered_n, missing_n from both
            for key in ["base_n", "answered_n", "missing_n"]:
                for evidence in [audience_evidence, total_evidence]:
                    v = evidence.get(key)
                    if v is not None:
                        try:
                            valid_counts.append(float(v))
                        except (TypeError, ValueError):
                            pass
        else:
            # Regular evidence_json (non-comparison, non-breakdown)
            categories = evidence_json.get("categories", [])
            for cat in categories:
                c = cat.get("count")
                p = cat.get("percent")
                if c is not None:
                    valid_counts.append(float(c))
                if p is not None:
                    valid_percents.append(float(p))

            stats = evidence_json.get("stats", {}) or {}
            for v in stats.values():
                if v is not None:
                    try:
                        valid_counts.append(float(v))
                    except (TypeError, ValueError):
                        pass

            for key in ["base_n", "answered_n", "missing_n"]:
                v = evidence_json.get(key)
                if v is not None:
                    try:
                        valid_counts.append(float(v))
                    except (TypeError, ValueError):
                        pass

        # Percentages in narrative: numbers followed by '%'
        percent_pattern = r'(\d+\.?\d*)\s*%'
        for match in re.finditer(percent_pattern, narrative_text):
            num_str = match.group(1)
            try:
                num_val = float(num_str)
            except (TypeError, ValueError):
                continue

            if not valid_percents:
                errors.append(f"Percentage {num_str}% not backed by evidence")
                continue

            closest = min(valid_percents, key=lambda x: abs(x - num_val))
            if abs(closest - num_val) > 1.0:  # ±1 percentage point tolerance
                errors.append(f"Percentage {num_str}% not found in evidence (closest: {closest:.2f}%)")

        # \"X out of Y\" patterns for counts
        out_of_pattern = r'(\d+)\s+out\s+of\s+(\d+)'
        for match in re.finditer(out_of_pattern, narrative_text.lower()):
            x_str, y_str = match.group(1), match.group(2)
            try:
                x_val = float(x_str)
                y_val = float(y_str)
            except (TypeError, ValueError):
                continue

            if valid_counts:
                if x_val not in valid_counts and y_val not in valid_counts:
                    errors.append(f"Counts '{x_str} out of {y_str}' not found in evidence counts")

        return errors
    
    def validate_quantifiers(
        self,
        narrative_text: str,
        evidence_json: Dict[str, Any]
    ) -> List[str]:
        """
        Validate quantifier phrases against evidence percentages
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        narrative_lower = narrative_text.lower()
        
        # Check each quantifier
        for phrase, threshold in self.quantifier_policy.items():
            if phrase in narrative_lower:
                # Find the relevant percent in evidence
                # This is simplified - in production, need to extract context
                categories = evidence_json.get('categories', [])
                if categories:
                    top_percent = categories[0].get('percent', 0) / 100.0
                    
                    # Check if phrase matches threshold
                    if 'majority' in phrase or 'all' in phrase:
                        if top_percent < threshold:
                            errors.append(f"Phrase '{phrase}' used but top category is only {top_percent*100:.1f}%, requires {threshold*100:.1f}%")
                    elif 'minority' in phrase or 'few' in phrase:
                        if top_percent > threshold:
                            errors.append(f"Phrase '{phrase}' used but top category is {top_percent*100:.1f}%, should be < {threshold*100:.1f}%")
        
        return errors
    
    def generate_structured_narrative(
        self,
        evidence_json: Dict[str, Any],
        question_text: str
    ) -> Dict[str, Any]:
        """
        Generate narrative for structured mode with number injection.
        
        All numbers are deterministically extracted from evidence_json as strings
        and then used to build the narrative. This ensures numbers are never
        invented by the LLM and can be validated against evidence.
        
        IMPORTANT: All statistics (counts, percentages) come from evidence_json
        which is computed deterministically via SQL aggregation. This service
        only formats and presents these numbers, never computes them.
        
        Supports:
        - Regular evidence_json (with categories)
        - Comparison evidence_json (with comparison_type="audience_vs_total")
        - Breakdown evidence_json (with cells array)
        
        Returns:
            Dict with narrative_text, key_points, caveats, evidence_recap
        """
        # Handle breakdown evidence_json (2D aggregation - X by Y)
        if 'cells' in evidence_json and evidence_json.get('cells'):
            cells = evidence_json.get('cells', [])
            base_n = evidence_json.get('base_n', 0)
            answered_n = evidence_json.get('answered_n', 0)
            primary_var_code = evidence_json.get('primary_variable_code', 'Unknown')
            group_by_var_code = evidence_json.get('group_by_variable_code', 'Unknown')
            
            if not cells:
                return {
                    'summary': f'{answered_n} cevabın çapraz analizi.',
                    'key_points': [],
                    'caveats': [],
                    'evidence_recap': {}
                }
            
            # Group cells by column (group_by variable) to find top patterns
            col_totals = {}  # {col_label: total_count}
            col_to_cells = {}  # {col_label: [cells]}
            
            for cell in cells:
                col_label = cell.get('col_label', 'Unknown')
                count = cell.get('count', 0)
                
                if col_label not in col_totals:
                    col_totals[col_label] = 0
                    col_to_cells[col_label] = []
                
                col_totals[col_label] += count
                col_to_cells[col_label].append(cell)
            
            # Find top column (group_by category) by total count
            top_col_label = max(col_totals.items(), key=lambda x: x[1])[0] if col_totals else None
            
            # Build narrative highlighting top patterns
            narrative_parts = []
            if top_col_label:
                top_col_cells = sorted(col_to_cells[top_col_label], key=lambda x: x.get('count', 0), reverse=True)
                top_cell = top_col_cells[0] if top_col_cells else None
                
                if top_cell:
                    row_label = top_cell.get('row_label', 'Unknown')
                    col_label = top_cell.get('col_label', 'Unknown')
                    count = top_cell.get('count', 0)
                    percent_of_col = top_cell.get('percent_of_col_valid', 0)
                    
                    narrative_parts.append(
                        f"{col_label} için, '{row_label}' en yaygın cevap oldu ({count} cevap, {col_label}'in %{percent_of_col:.1f}'i)."
                    )
            
            # Add summary about breakdown structure
            unique_cols = len(col_totals)
            unique_rows = len(set(cell.get('row_label') for cell in cells))
            
            narrative_parts.append(
                f"Çapraz analiz, {unique_cols} {group_by_var_code} grubu arasında {unique_rows} cevap kategorisi gösteriyor."
            )
            
            return {
                'summary': ' '.join(narrative_parts) if narrative_parts else f'{answered_n} cevabın çapraz analizi.',
                'key_points': [
                    {
                        'text': f'Ana değişken: {primary_var_code}',
                        'evidence_ref': {'primary_variable_code': primary_var_code}
                    },
                    {
                        'text': f'Gruplandırma: {group_by_var_code}',
                        'evidence_ref': {'group_by_variable_code': group_by_var_code}
                    },
                    {
                        'text': f'Toplam cevap: {answered_n}',
                        'evidence_ref': {'answered_n': answered_n}
                    }
                ],
                'caveats': [f'Çapraz analiz {primary_var_code} değişkeninin {group_by_var_code} değişkenine göre çapraz tablosunu gösteriyor'],
                'evidence_recap': {
                    'base_n': base_n,
                    'answered_n': answered_n,
                    'unique_rows': unique_rows,
                    'unique_cols': unique_cols
                }
            }
        
        # Handle comparison evidence_json
        if evidence_json.get('comparison_type') == 'audience_vs_total':
            # For comparison, use audience evidence_json for narrative generation
            # The chart_json will handle the comparison visualization
            audience_evidence = evidence_json.get('audience', {})
            total_evidence = evidence_json.get('total', {})
            
            # Generate a comparison narrative
            audience_categories = audience_evidence.get('categories', [])
            total_categories = total_evidence.get('categories', [])
            audience_base_n = audience_evidence.get('base_n', 0)
            total_base_n = total_evidence.get('base_n', 0)
            
            if not audience_categories or not total_categories:
                return {
                    'summary': 'Karşılaştırma verisi mevcut değil.',
                    'key_points': [],
                    'caveats': [],
                    'evidence_recap': {}
                }
            
            # Build comparison narrative - highlight top category differences
            narrative_parts = []
            if audience_categories and total_categories:
                audience_top = audience_categories[0]
                total_top = total_categories[0]
                
                audience_pct = audience_top.get('percent', 0)
                total_pct = total_top.get('percent', 0)
                diff = audience_pct - total_pct
                
                narrative_parts.append(
                    f"{audience_top.get('label', 'en üst kategori')} için, "
                    f"hedef kitle %{audience_pct:.1f} gösterirken toplam örnekte %{total_pct:.1f} "
                    f"({abs(diff):.1f} yüzde puanı {'daha yüksek' if diff > 0 else 'daha düşük'})."
                )
            
            return {
                'summary': ' '.join(narrative_parts) if narrative_parts else 'Karşılaştırma tamamlandı.',
                'key_points': [],
                'caveats': [f"Hedef kitle örnek boyutu: {audience_base_n}, Toplam örnek boyutu: {total_base_n}"],
                'evidence_recap': {
                    'audience_base_n': audience_base_n,
                    'total_base_n': total_base_n,
                }
            }
        
        # Regular evidence_json (non-comparison)
        categories = evidence_json.get('categories', [])
        base_n = evidence_json.get('base_n', 0)
        answered_n = evidence_json.get('answered_n', 0)
        missing_n = evidence_json.get('missing_n', 0)
        response_rate = evidence_json.get('response_rate', 0.0)
        
        # Extract numbers as strings from evidence_json (number injection)
        base_n_str = str(base_n)
        answered_n_str = str(answered_n)
        missing_n_str = str(missing_n)
        
        # Convert response_rate to percentage string (0.0-100.0)
        if isinstance(response_rate, (int, float)):
            response_rate_pct = round(response_rate * 100, 1) if response_rate <= 1.0 else round(response_rate, 1)
            response_rate_str = f"{response_rate_pct:.1f}"
        else:
            response_rate_str = "0.0"
        
        # Build narrative using injected numbers
        narrative_parts = []
        if categories:
            top_cat = categories[0]
            # Extract numbers as strings from category
            cat_label = top_cat.get('label', 'Unknown')
            cat_percent_str = f"{top_cat.get('percent', 0):.1f}"  # Formatted as string
            cat_count_str = str(top_cat.get('count', 0))
            
            # Build narrative using these exact string values
            narrative_parts.append(
                f"{cat_label}, katılımcıların %{cat_percent_str}'i tarafından seçildi ({answered_n_str} kişiden {cat_count_str} kişi)."
            )
        
        narrative_text = " ".join(narrative_parts) if narrative_parts else f"{answered_n_str} cevabın analizi."
        
        # Build key_points using injected numbers
        key_points = [
            {
                "text": f"Temel örnek boyutu: {base_n_str}",
                "evidence_ref": {"base_n": base_n}
            },
            {
                "text": f"Cevap oranı: %{response_rate_str}",
                "evidence_ref": {"response_rate": response_rate}
            }
        ]
        
        if categories:
            for cat in categories[:3]:
                cat_label = cat.get('label', 'Unknown')
                cat_percent_str = f"{cat.get('percent', 0):.1f}"
                cat_count_str = str(cat.get('count', 0))
                
                key_points.append({
                    "text": f"{cat_label}: {cat_percent_str}% ({cat_count_str})",
                    "evidence_ref": {
                        "category_index": categories.index(cat),
                        "percent": round(cat.get('percent', 0), 1),
                        "count": cat.get('count', 0)
                    }
                })
        
        return {
            "summary": narrative_text,
            "key_points": key_points,
            "quantifiers": [],
            "caveats": [
                f"Cevap oranı: %{response_rate_str}",
                f"Eksik cevaplar: {missing_n_str}"
            ],
            "evidence_recap": {
                "base_n": base_n,
                "top_categories": categories[:5]
            }
        }
    
    def generate_rag_narrative(
        self,
        evidence_json: Dict[str, Any],
        synthesis_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate narrative for RAG mode from synthesis result.
        
        The synthesis_result should come from RAGService.synthesize_with_llm,
        which provides themes and narrative based on citations.
        
        Args:
            evidence_json: Evidence JSON with citations
            synthesis_result: Optional synthesis result from RAGService.synthesize_with_llm
                If not provided, generates a basic narrative
        
        Returns:
            Dict with narrative_text, themes, caveats
        """
        citations = evidence_json.get('citations', [])
        
        # Use synthesis result if provided
        if synthesis_result:
            themes = synthesis_result.get('themes', [])
            narrative_text = synthesis_result.get('narrative', '')
            caveats = synthesis_result.get('caveats', [])
        else:
            # Fallback to basic narrative
            themes = []
            narrative_parts = []
            for theme in themes:
                narrative_parts.append(f"{theme.get('description', '')}: {theme.get('support_count', 0)} responses")
            narrative_text = ". ".join(narrative_parts) if narrative_parts else f"{len(citations)} ilgili cevap bulundu."
            caveats = [
                "Sonuçlar alınan örneğe dayanmaktadır, nüfus yüzdelerine değil",
                f"Örnek boyutu: {len(citations)}"
            ]
        
        return {
            "narrative": narrative_text,
            "themes": themes,
            "caveats": caveats
        }
    
    def validate_and_generate(
        self,
        evidence_json: Dict[str, Any],
        question_text: str,
        mode: str,
        narrative_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate narrative and return safe result
        
        Returns:
            Dict with narrative_text, errors, is_valid
        """
        if not narrative_output:
            # Generate narrative
            if mode == "structured":
                narrative_output = self.generate_structured_narrative(evidence_json, question_text)
                narrative_text = narrative_output.get('summary', '')
            else:
                # RAG mode: synthesis_result should be passed via evidence_json or separately
                # For now, use None to trigger fallback
                synthesis_result = evidence_json.get('synthesis_result')
                narrative_output = self.generate_rag_narrative(evidence_json, synthesis_result)
                narrative_text = narrative_output.get('narrative', '')
        else:
            narrative_text = narrative_output.get('narrative_text') or narrative_output.get('summary') or narrative_output.get('narrative', '')
        
        # Validate
        quantifier_errors: List[str] = []

        if mode == "structured":
            # Structured mode: numbers are already deterministically injected
            # from evidence_json; we only validate explicit percentages and
            # \"X out of Y\" patterns to guard against accidental changes.
            number_errors = self.validate_structured_numbers(narrative_text, evidence_json)
            quantifier_errors = self.validate_quantifiers(narrative_text, evidence_json)
            all_errors = number_errors + quantifier_errors
        else:
            # RAG mode: No numeric validation needed.
            # RAG narratives come from LLM synthesis of citations, and don't contain
            # statistical numbers that need validation. The synthesis_result contains
            # themes and quotes, not numerical statistics.
            all_errors = []
        
        if all_errors:
            return {
                "narrative_text": "Veri uyumsuzluğu—güvenli anlatı oluşturulamadı.",
                "errors": all_errors,
                "is_valid": False,
                "original_narrative": narrative_text
            }
        
        return {
            "narrative_text": narrative_text,
            "narrative_output": narrative_output,
            "errors": [],
            "is_valid": True
        }


# Singleton instance
narration_service = NarrationService()

