"""
Question router service
Routes questions to either Structured (Mode A) or RAG (Mode B) mode
Uses 2-stage variable mapping: embedding-based candidate selection + deterministic scoring
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import re
import logging

from models import Variable, Dataset, Audience
from services.embedding_service import embedding_service
from services.intent_classification_service import intent_classification_service
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class QuestionRouterService:
    """Service for routing questions to appropriate mode"""
    
    def __init__(self):
        # Negation patterns (English and Turkish)
        self.negation_patterns = {
            'not': ['not', "n't", 'no', 'never', 'none', 'nothing', 'nobody', 'nowhere'],
            'except': ['except', 'exclude', 'excluding', 'other than'],
            'least': ['least', 'lowest', 'smallest', 'minimum'],
            'turkish_not': ['değil', 'yok', 'hayır', 'hiç', 'hiçbir'],
            'turkish_except': ['hariç', 'dışında', 'başka'],
            'turkish_least': ['en az', 'en düşük', 'en küçük', 'minimum']
        }
        
        # Comparison patterns
        self.comparison_patterns = ['vs', 'versus', 'compare', 'comparison', 'difference', 'diff', 'kıyasla', 'fark']
        # Patterns that indicate "vs total sample" comparison
        self.vs_total_patterns = ['vs total', 'versus total', 'vs total sample', 'versus total sample', 'vs all', 'versus all']

        # Structured-intent keywords: when present, we strongly prefer Mode A
        # if a reasonable variable mapping exists.
        self.structured_keywords = [
            # English
            "distribution", "frequency", "count", "counts", "%", "percent", "percentage",
            "share", "proportion", "base n", "valid n", "response rate",
            "average", "mean", "median", "min", "max", "standard deviation", "std dev",
            "stats", "top", "bottom",
            "compare", "vs", "versus", "difference", "lift", "higher", "lower", "gap",
            "by", "breakdown", "split", "segment", "cohort", "group", "crosstab", "cross tab", "cross-tab",
            "how many", "what share", "what percent",
            # Turkish
            "dağılım", "frekans", "adet", "sayı", "yüzde", "oran",
            "ortalama", "medyan", "istatistik", "min", "max",
            "karşılaştır", "kıyasla", "fark", "vs",
            "kırılım", "segment", "gruba göre", "e göre",
        ]

        # RAG-intent keywords: exploratory \"why/describe/themes\" questions
        self.rag_keywords = [
            # English
            "why", "reason", "reasons", "explain", "describe", "feedback",
            "complaints", "frustrations", "what do they dislike", "themes",
            "motivations", "barriers",
            # Turkish
            "neden", "niye", "açıkla", "tanımla", "geri bildirim",
            "şikayet", "şikayetler", "sıkıntı", "rahatsız", "nedenleri",
        ]
    
    def normalize_question(self, question: str) -> str:
        """
        Normalize question text
        - Lowercase
        - Trim whitespace
        - Remove punctuation
        - Unify whitespace
        """
        # Lowercase
        normalized = question.lower()
        
        # Remove punctuation (keep essential ones)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Unify whitespace
        normalized = ' '.join(normalized.split())
        
        # Trim
        normalized = normalized.strip()
        
        return normalized
    
    def detect_negation(self, question: str) -> Dict[str, Any]:
        """
        Detect negation and comparison intent
        Returns AST structure for negation handling
        
        Returns:
            Dict with type, targets, operator, notes
        """
        normalized = self.normalize_question(question)
        negation_ast = None
        
        # Check for comparison
        has_comparison = any(pattern in normalized for pattern in self.comparison_patterns)
        
        if has_comparison:
            # Extract comparison targets (simplified)
            # TODO: More sophisticated extraction
            negation_ast = {
                "type": "COMPARE",
                "targets": [],  # Will be populated based on question analysis
                "operator": "COMPARE",
                "notes": "Comparison detected"
            }
        
        # Check for EXCEPT pattern
        for pattern in self.negation_patterns['except'] + self.negation_patterns['turkish_except']:
            if pattern in normalized:
                # Extract excluded targets (simplified)
                negation_ast = {
                    "type": "EXCEPT",
                    "targets": [],  # Will be populated from question
                    "operator": "NOT_IN",
                    "notes": f"Exception pattern detected: {pattern}"
                }
                break
        
        # Check for NOT pattern
        if not negation_ast:
            for pattern in self.negation_patterns['not'] + self.negation_patterns['turkish_not']:
                if pattern in normalized:
                    negation_ast = {
                        "type": "NOT",
                        "targets": [],
                        "operator": "!=",
                        "notes": f"Negation pattern detected: {pattern}"
                    }
                    break
        
        # Check for LEAST pattern
        if not negation_ast:
            for pattern in self.negation_patterns['least'] + self.negation_patterns['turkish_least']:
                if pattern in normalized:
                    negation_ast = {
                        "type": "LEAST",
                        "targets": [],
                        "operator": "MIN",
                        "notes": f"Least pattern detected: {pattern}"
                    }
                    break
        
        return negation_ast or {
            "type": "NONE",
            "targets": [],
            "operator": None,
            "notes": "No negation detected"
        }
    
    def score_variable_match(
        self,
        question: str,
        variable: Variable,
        embedding_similarity: float,
        structured_intent: bool = False
    ) -> Tuple[float, Dict[str, float]]:
        """
        Deterministic match scorer (NOT LLM)
        
        Returns:
            Tuple of (total_score, component_scores)
        """
        normalized_q = self.normalize_question(question)
        components = {}
        
        # 1. Semantic similarity score (from embedding)
        components['semantic'] = embedding_similarity
        
        # 2. Lexical overlap score
        # Extract keywords from question
        q_words = set(normalized_q.split())
        
        # Get text to match against
        var_text = ""
        if variable.question_text:
            var_text += variable.question_text.lower()
        if variable.label:
            var_text += " " + variable.label.lower()
        if variable.code:
            var_text += " " + variable.code.lower()
        
        # Get value labels text
        value_labels_text = ""
        if variable.value_labels and isinstance(variable.value_labels, list):
            for vl in variable.value_labels[:20]:  # Limit to first 20
                if isinstance(vl, dict):
                    label = vl.get('label', '')
                    if label:
                        value_labels_text += " " + label.lower()
                else:
                    value_labels_text += " " + str(vl).lower()
        
        var_words = set(var_text.split())
        value_label_words = set(value_labels_text.split())
        all_var_words = var_words | value_label_words
        
        # Jaccard similarity
        if all_var_words:
            intersection = len(q_words & all_var_words)
            union = len(q_words | all_var_words)
            lexical_score = intersection / union if union > 0 else 0.0
        else:
            lexical_score = 0.0
        
        components['lexical'] = lexical_score
        
        # 3. Value label coverage
        # Check if question terms appear in value labels
        if value_label_words:
            coverage = len(q_words & value_label_words) / len(q_words) if q_words else 0.0
        else:
            coverage = 0.0
        components['value_label_coverage'] = coverage
        
        # 4. Question family heuristics
        family_score = 0.0
        
        # Demographic boost (enhanced with more keywords)
        if variable.is_demographic:
            demog_keywords = [
                'who', 'age', 'income', 'gender', 'sex', 'region', 'education', 
                'demographic', 'generation', 'cohort', 'kim', 'yaş', 'gelir', 
                'cinsiyet', 'bölge', 'eğitim', 'demografi', 'kuşak', 'yaş grubu',
                'age group', 'age band', 'income band', 'income group'
            ]
            if any(kw in normalized_q for kw in demog_keywords):
                family_score += 0.2
        
        # Yes/No boost for single-choice
        if variable.var_type == 'single_choice':
            yesno_keywords = ['yes', 'no', 'do', 'does', 'is', 'are', 'evet', 'hayır', 'mi', 'mı']
            if any(kw in normalized_q for kw in yesno_keywords):
                family_score += 0.15
        
        # Open-text boost detection (but will route to Mode B)
        if variable.var_type == 'text':
            why_keywords = ['why', 'how', 'describe', 'explain', 'neden', 'nasıl', 'açıkla']
            if any(kw in normalized_q for kw in why_keywords):
                family_score += 0.1  # Lower boost since it routes to Mode B
        
        components['question_family'] = min(family_score, 0.3)  # Cap at 0.3
        
        # 5. Type suitability
        type_score = 0.0
        # This is variable type dependent matching
        # For now, basic heuristic
        if variable.var_type in ['single_choice', 'multi_choice']:
            # Questions about categories/choices
            if any(word in normalized_q for word in ['what', 'which', 'category', 'option', 'choice', 'hangi', 'seçenek']):
                type_score = 0.15
        elif variable.var_type == 'numeric':
            # Questions about numbers/amounts
            if any(word in normalized_q for word in ['how much', 'how many', 'number', 'amount', 'count', 'kaç', 'sayı']):
                type_score = 0.15
        
        # Boost type_suitability if structured intent is detected
        if structured_intent:
            type_score *= 1.5  # Increase weight for structured questions
        
        components['type_suitability'] = type_score
        
        # Composite score (weighted combination)
        # If structured intent, slightly boost type_suitability weight
        if structured_intent:
            total_score = (
                components['semantic'] * 0.4 +
                components['lexical'] * 0.3 +
                components['value_label_coverage'] * 0.15 +
                components['question_family'] * 0.1 +
                components['type_suitability'] * 0.08  # Slightly increased weight
            )
        else:
            total_score = (
                components['semantic'] * 0.4 +
                components['lexical'] * 0.3 +
                components['value_label_coverage'] * 0.15 +
                components['question_family'] * 0.1 +
                components['type_suitability'] * 0.05
            )
        
        return total_score, components
    
    def get_dynamic_threshold(self, var_type: Optional[str], is_demographic: bool = False) -> float:
        """Get dynamic threshold based on variable type"""
        if is_demographic:
            return 0.80  # Higher confidence needed for demographics
        elif var_type == 'single_choice':
            return 0.75
        elif var_type in ['numeric', 'scale']:
            return 0.72
        elif var_type == 'text':
            return 0.60  # Lower threshold, routes to Mode B anyway
        else:
            return 0.70  # Default
    
    def _extract_var_codes_from_question(self, question_text: str) -> List[str]:
        """
        Extract variable codes from question text using regex
        Looks for patterns like D1_GEN, S2_R1, Q3_5, S3_T, etc.
        Variable codes typically contain underscores, numbers, or are very short (2-4 chars)
        """
        # Pattern: letters/numbers/underscore, typically starts with letter
        # Examples: D1_GEN, S2_R1, Q3_5, S3_T, AGE_BAND, etc.
        pattern = r'\b[A-Z][A-Z0-9_]{1,30}\b'
        matches = re.findall(pattern, question_text.upper())
        
        # Filter out common English words and invalid patterns
        # Variable codes typically:
        # - Contain an underscore (e.g., D1_GEN, S3_T)
        # - OR contain a digit (e.g., D1GEN, S3T, Q5)
        # - OR are 2-4 characters (e.g., AGE, Q1)
        # - Are NOT common English words
        common_words = {
            'THIS', 'WHAT', 'WHERE', 'WHEN', 'WHY', 'HOW', 'WHICH', 'WHO', 
            'WITHIN', 'GIVE', 'COUNTS', 'VALID', 'AND', 'THE', 'OF', 'TO', 
            'A', 'AN', 'IS', 'ARE', 'DO', 'DOES', 'DID', 'WAS', 'WERE', 
            'WILL', 'WOULD', 'CAN', 'COULD', 'SHOULD', 'MAY', 'MIGHT',
            'BABY', 'BOOMERS', 'AUDIENCE', 'DISTRIBUTION', 'YOU', 'LIVE',
            'SHOW', 'WITH', 'FOR', 'FROM', 'THAT', 'THESE', 'THOSE'
        }
        
        filtered = []
        for m in matches:
            # Skip if it's a common word
            if m in common_words:
                continue
            
            # Skip single letters
            if len(m) == 1:
                continue
            
            # Include if it has underscore (D1_GEN, S3_T)
            if '_' in m:
                filtered.append(m)
                continue
            
            # Include if it has a digit (D1GEN, S3T, Q5)
            if any(c.isdigit() for c in m):
                filtered.append(m)
                continue
            
            # Include if it's 2-4 chars (AGE, Q1, GEN)
            if 2 <= len(m) <= 4:
                filtered.append(m)
        
        return filtered
    
    def detect_breakdown_pattern(
        self,
        question_text: str,
        db: Session,
        dataset_id: str
    ) -> Optional[int]:
        """
        Detect "X by Y" / "X'e göre Y" breakdown patterns.
        Returns group_by_variable_id if detected, None otherwise.
        
        Args:
            question_text: Original question text
            db: Database session
            dataset_id: Dataset ID
            
        Returns:
            Optional[int]: group_by_variable_id if breakdown detected, None otherwise
        """
        normalized = self.normalize_question(question_text)
        
        # Patterns for breakdown detection
        breakdown_patterns = [
            r'(\w+)\s+by\s+(\w+)',  # "age by region"
            r'(\w+)\s+e\s+göre\s+(\w+)',  # "X'e göre Y"
            r'breakdown\s+(\w+)\s+by\s+(\w+)',  # "breakdown age by region"
            r'kırılım\s+(\w+)\s+e\s+göre\s+(\w+)',  # "kırılım X'e göre Y"
        ]
        
        for pattern in breakdown_patterns:
            matches = re.findall(pattern, normalized)
            if matches:
                # For now, take the last match (most specific)
                # matches[0] could be (group1, group2) tuple
                if isinstance(matches[0], tuple) and len(matches[0]) == 2:
                    group_by_term = matches[0][1]  # Second term is the "by Y" part
                    
                    # Try to find variable matching this term
                    # Simple approach: search by code or label containing the term
                    variables = db.query(Variable).filter(
                        Variable.dataset_id == dataset_id
                    ).all()
                    
                    for var in variables:
                        # Check if group_by_term matches variable code or label
                        var_code_lower = (var.code or '').lower()
                        var_label_lower = (var.label or '').lower()
                        
                        if group_by_term in var_code_lower or group_by_term in var_label_lower:
                            return var.id
        
        return None
    
    def detect_audience_override(
        self,
        db: Session,
        dataset_id: str,
        question_text: str,
        current_audience_id: Optional[str]
    ) -> Optional[str]:
        """
        Detect if question text specifies a different audience (e.g., "for female", "for not female", "for male")
        If detected, returns the appropriate audience_id. Returns None if no override or if total sample requested.
        
        Examples:
        - "What is the distribution of QV1_1 for female respondents?" -> returns female audience_id
        - "What is the distribution of QV1_1 for not female respondents?" -> returns None (total sample, no audience filter)
        - "What is the distribution of QV1_1 for male respondents?" -> returns male audience_id
        """
        normalized = self.normalize_question(question_text)
        
        # Patterns to detect audience mentions in question
        audience_patterns = {
            'female': [r'for\s+female', r'female\s+respondents', r'females'],
            'not_female': [r'for\s+not\s+female', r'for\s+non[\s-]?female', r'not\s+female\s+respondents'],
            'male': [r'for\s+male', r'male\s+respondents', r'males'],
        }
        
        # Check for "not female" or "non-female" first (more specific)
        for pattern in audience_patterns['not_female']:
            if re.search(pattern, normalized):
                # "Not female" means total sample (no audience filter)
                logger.info(f"Question requests 'not female' audience - using total sample (no audience filter)")
                return None  # None means total sample
        
        # Check for "female"
        for pattern in audience_patterns['female']:
            if re.search(pattern, normalized):
                # Try to find existing female audience in dataset
                audiences = db.query(Audience).filter(
                    Audience.dataset_id == dataset_id
                ).all()
                
                for audience in audiences:
                    filter_json = audience.filter_json or {}
                    # Look for gender variable with female value
                    for var_key in ['D1_GENDER', 'D2_GENDER', 'GENDER', 'D1_SEX', 'D2_SEX', 'SEX']:
                        if var_key in filter_json:
                            filter_cond = filter_json.get(var_key, {})
                            if isinstance(filter_cond, dict):
                                values = filter_cond.get('values', [])
                                # Check if includes female value (usually "2" or "Female")
                                if any(str(v).lower() in ['2', 'female', 'f'] for v in values):
                                    logger.info(f"Found female audience: {audience.id} ({audience.name})")
                                    return audience.id
        
        # Check for "male"
        for pattern in audience_patterns['male']:
            if re.search(pattern, normalized):
                audiences = db.query(Audience).filter(
                    Audience.dataset_id == dataset_id
                ).all()
                
                for audience in audiences:
                    filter_json = audience.filter_json or {}
                    for var_key in ['D1_GENDER', 'D2_GENDER', 'GENDER', 'D1_SEX', 'D2_SEX', 'SEX']:
                        if var_key in filter_json:
                            filter_cond = filter_json.get(var_key, {})
                            if isinstance(filter_cond, dict):
                                values = filter_cond.get('values', [])
                                # Check if includes male value (usually "1" or "Male")
                                if any(str(v).lower() in ['1', 'male', 'm'] for v in values):
                                    logger.info(f"Found male audience: {audience.id} ({audience.name})")
                                    return audience.id
        
        # No audience override detected
        return current_audience_id
    
    async def route_question(
        self,
        db: Session,
        dataset_id: str,
        audience_id: Optional[str],
        question_text: str
    ) -> Dict[str, Any]:
        """
        Route question to appropriate mode
        
        Returns:
            Dict with mode, mapped_variables, negation_flags, mapping_debug_json, override_audience_id
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        # Step 0: Check if question text overrides audience
        override_audience_id = self.detect_audience_override(
            db=db,
            dataset_id=dataset_id,
            question_text=question_text,
            current_audience_id=audience_id
        )
        
        # Use override_audience_id if specified, otherwise use original audience_id
        effective_audience_id = override_audience_id if override_audience_id != audience_id else audience_id
        
        # Step 0: Normalize
        normalized_question = self.normalize_question(question_text)

        # Detect high-level intent
        structured_intent = any(kw in normalized_question for kw in self.structured_keywords)
        rag_intent = any(kw in normalized_question for kw in self.rag_keywords)
        
        # Detect breakdown pattern ("X by Y")
        group_by_variable_id = self.detect_breakdown_pattern(
            question_text=question_text,
            db=db,
            dataset_id=dataset_id
        )
        
        # Detect "vs total" comparison pattern
        comparison_audience_id = None
        if effective_audience_id:
            # Check if question contains "vs total" or similar patterns
            if any(pattern in normalized_question for pattern in self.vs_total_patterns):
                comparison_audience_id = effective_audience_id
                logger.info(f"Comparison detected: audience {effective_audience_id} vs total sample")
        
        # Step 0.5: CRITICAL - Check for explicit variable code FIRST
        # If user explicitly mentions a variable code (e.g., "D1_R3 distribution"),
        # route to structured mode regardless of decision intent detection
        # This ensures direct variable queries are handled correctly
        potential_var_codes = self._extract_var_codes_from_question(question_text)
        hard_mapped_variable = None
        if potential_var_codes:
            for var_code in potential_var_codes:
                variable = db.query(Variable).filter(
                    Variable.dataset_id == dataset_id,
                    Variable.code == var_code
                ).first()
                if variable:
                    hard_mapped_variable = variable
                    logger.info(f"Found explicit variable code in question: {var_code}, routing to structured mode")
                    # Explicit variable code found - route to structured mode
                    # Step 2: Detect negation
                    negation_ast = self.detect_negation(question_text)
                    
                    return {
                        "mode": "structured",
                        "mapped_variables": [variable.id],
                        "group_by_variable_id": group_by_variable_id,
                        "comparison_audience_id": comparison_audience_id,
                        "override_audience_id": override_audience_id,
                        "negation_flags": negation_ast,
                        "mapping_debug_json": {
                            "hard_mapped": True,
                            "chosen_var_code": var_code,
                            "reason": f"Explicit variable code detected: {var_code}",
                            "structured_intent": structured_intent,
                            "rag_intent": rag_intent,
                            "normalized_question": normalized_question
                        }
                    }
        
        # Step 1: Detect decision/normative intent (ONLY if no explicit variable code found)
        # (This happens AFTER checking for explicit variable codes)
        decision_intent_result = None
        try:
            decision_intent_result = intent_classification_service.detect_decision_intent(
                question_text=question_text,
                threshold=0.65  # 65% similarity threshold
            )
            decision_intent = decision_intent_result.get("is_decision_intent", False)
            logger.info(f"Decision intent detection: {decision_intent} (method: {decision_intent_result.get('method')}, score: {decision_intent_result.get('similarity', 0):.3f})")
        except Exception as e:
            logger.warning(f"Error in decision intent detection, falling back to keyword-only: {e}")
            decision_intent = False
            decision_intent_result = {"is_decision_intent": False, "method": "error", "reason": str(e)}
        
        # Step 2: Check for decision intent - if detected, route to decision_proxy mode
        # (This happens AFTER checking for explicit variable codes)
        if decision_intent_result and decision_intent_result.get("is_decision_intent", False):
            # Decision intent detected - route to decision_proxy mode
            # We still try to find a proxy target variable, but don't require it
            proxy_target_variable_id = None
            candidate_variables = []
            
            # Try to find a potential target variable (optional for decision_proxy)
            # This will be done in DecisionProxyService, but we can pre-populate here
            # For now, return decision_proxy mode with empty variables
            # The DecisionProxyService will handle variable identification
            
            return {
                "mode": "decision_proxy",
                "mapped_variables": [],  # Will be populated by DecisionProxyService
                "group_by_variable_id": group_by_variable_id,
                "comparison_audience_id": comparison_audience_id,
                "override_audience_id": override_audience_id,
                "negation_flags": self.detect_negation(question_text),
                "mapping_debug_json": {
                    "decision_intent_detected": True,
                    "decision_intent_result": decision_intent_result,
                    "structured_intent": structured_intent,
                    "rag_intent": rag_intent,
                    "normalized_question": normalized_question,
                    "reason": f"Decision intent detected via {decision_intent_result.get('method')} method"
                }
            }
        
        # Step 3: Detect negation
        negation_ast = self.detect_negation(question_text)
        
        # Step 4: Hard-map if variable code is mentioned in question (fallback, already checked above)
        # Extract potential var codes from question
        
        # Check if any extracted code exists in database
        hard_mapped_variable = None
        if potential_var_codes:
            for var_code in potential_var_codes:
                variable = db.query(Variable).filter(
                    Variable.dataset_id == dataset_id,
                    Variable.code == var_code
                ).first()
                
                if variable:
                    hard_mapped_variable = variable
                    logger.info(f"Hard-mapping to variable {var_code} (variable_id: {variable.id}) based on exact code match in question")
                    break
        
        # If hard-mapped, use structured mode directly
        if hard_mapped_variable:
            # Check if variable type supports structured aggregation
            var_type = hard_mapped_variable.var_type or 'unknown'
            if var_type in ['single_choice', 'multi_choice', 'numeric', 'scale', 'ordinal']:
                return {
                    "mode": "structured",
                    "mapped_variables": [hard_mapped_variable.id],
                    "group_by_variable_id": group_by_variable_id,
                    "comparison_audience_id": comparison_audience_id,
                    "negation_flags": negation_ast,
                    "mapping_debug_json": {
                        "candidates": [],
                        "chosen_variable_id": hard_mapped_variable.id,
                        "chosen_var_code": hard_mapped_variable.code,
                        "group_by_variable_id": group_by_variable_id,
                        "comparison_audience_id": comparison_audience_id,
                        "reason": f"Hard-mapped via exact var_code match: {hard_mapped_variable.code}",
                        "threshold_used": "N/A (hard-map)",
                        "mode_selected": "structured",
                        "structured_intent": structured_intent or True,
                        "rag_intent": rag_intent,
                        "hard_mapped": True,
                        "normalized_question": normalized_question,
                    }
                }
        
        # Step 3: Variable mapping (2-stage) - only if no hard-map
        # Stage 1: Embedding-based candidate selection
        query_embedding = embedding_service.generate_embedding(question_text)
        if not query_embedding:
            logger.warning("Failed to generate query embedding, defaulting to RAG mode")
            return {
                "mode": "rag",
                "mapped_variables": [],
                "override_audience_id": override_audience_id,
                "negation_flags": negation_ast,
                "mapping_debug_json": {
                    "error": "Failed to generate query embedding",
                    "normalized_question": normalized_question
                }
            }
        
        # Get top 30 candidates from embedding search
        candidates = embedding_service.get_variable_embeddings(
            db=db,
            dataset_id=dataset_id,
            query_vector=query_embedding,
            top_k=30
        )
        
        if not candidates:
            logger.warning("No variable candidates found, defaulting to RAG mode")
            return {
                "mode": "rag",
                "mapped_variables": [],
                "override_audience_id": override_audience_id,
                "negation_flags": negation_ast,
                "mapping_debug_json": {
                    "candidates": [],
                    "normalized_question": normalized_question,
                    "reason": "No variable candidates found"
                }
            }
        
        # Stage 2: Deterministic scoring
        scored_candidates = []
        for candidate in candidates:
            variable_id = candidate['variable_id']
            embedding_sim = candidate['score']  # Already similarity (1 - distance)
            
            variable = db.query(Variable).filter(Variable.id == variable_id).first()
            if not variable:
                continue
            
            total_score, components = self.score_variable_match(
                question=question_text,
                variable=variable,
                embedding_similarity=embedding_sim,
                structured_intent=structured_intent
            )
            
            scored_candidates.append({
                "variable_id": variable_id,
                "var_code": variable.code,
                "var_type": variable.var_type,
                "is_demographic": variable.is_demographic,
                "score": total_score,
                "components": components
            })
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Get top 3
        top_3 = scored_candidates[:3]
        
        if not top_3:
            return {
                "mode": "rag",
                "mapped_variables": [],
                "group_by_variable_id": group_by_variable_id,
                "comparison_audience_id": comparison_audience_id,
                "override_audience_id": override_audience_id,
                "negation_flags": negation_ast,
                "mapping_debug_json": {
                    "candidates": [],
                    "normalized_question": normalized_question,
                    "reason": "No scored candidates"
                }
            }
        
        # Check threshold (optionally biased by structured intent)
        top_candidate = top_3[0]
        base_threshold = self.get_dynamic_threshold(
            var_type=top_candidate['var_type'],
            is_demographic=top_candidate['is_demographic']
        )
        # If the question clearly asks for counts/%/distribution, allow a small margin
        # below the normal threshold to still pick structured mode.
        if structured_intent:
            threshold = max(0.0, base_threshold - 0.05)
        else:
            threshold = base_threshold
        
        chosen_variable = None
        mode = "rag"
        reason = ""
        
        if top_candidate['score'] >= threshold:
            # Check if variable type supports structured aggregation
            var_type = top_candidate['var_type']
            if var_type in ['single_choice', 'multi_choice', 'numeric', 'scale']:
                mode = "structured"
                chosen_variable = top_candidate
                reason = f"High score ({top_candidate['score']:.2f}) >= threshold ({threshold:.2f}), type supports structured aggregation"
            elif var_type == 'text':
                mode = "rag"  # Open-text routes to Mode B (variable-specific RAG)
                chosen_variable = top_candidate
                reason = f"Open-text variable detected, routing to variable-specific RAG"
        else:
            # If structured intent exists but we can't confidently map to a variable,
            # log this explicitly; still fall back to RAG so the user at least gets
            # some qualitative signal instead of an error.
            if structured_intent:
                reason = (
                    f"Structured intent detected but score ({top_candidate['score']:.2f}) "
                    f"< threshold ({threshold:.2f}); defaulting to RAG"
                )
            else:
                reason = f"Score ({top_candidate['score']:.2f}) < threshold ({threshold:.2f}), defaulting to RAG"
        
        # Build mapping_debug_json
        mapping_debug_json = {
            "candidates": top_3,
            "chosen_variable_id": chosen_variable['variable_id'] if chosen_variable else None,
            "chosen_var_code": chosen_variable['var_code'] if chosen_variable else None,
            "group_by_variable_id": group_by_variable_id,
            "comparison_audience_id": comparison_audience_id,
            "reason": reason,
            "threshold_used": threshold,
            "mode_selected": mode,
            "structured_intent": structured_intent,
            "rag_intent": rag_intent,
            "decision_intent": decision_intent_result.get("has_decision_intent", False) if decision_intent_result else False,
            "decision_intent_result": decision_intent_result if decision_intent_result else None,
            "hard_mapped": False,
            "normalized_question": normalized_question,
        }
        
        # Add comparison_audience_id to mapping_debug_json
        mapping_debug_json['comparison_audience_id'] = comparison_audience_id
        
        return {
            "mode": mode,
            "mapped_variables": [top_candidate['variable_id']] if chosen_variable else [],
            "group_by_variable_id": group_by_variable_id,
            "comparison_audience_id": comparison_audience_id,
            "negation_flags": negation_ast,
            "mapping_debug_json": mapping_debug_json
        }


# Singleton instance
question_router_service = QuestionRouterService()

