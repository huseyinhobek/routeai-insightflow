"""
Decision Proxy Service
Handles normative/decision questions (best/should/logical choice) without hallucination.
Produces data-backed proxy answers and assumption-based decision rules.

Implements "Proxy Ladder" fallback system:
- Tier0: Direct preference/choice variables
- Tier1: Behavioral variables (purchase, usage)
- Tier2: Attitudinal variables (trust, value, quality)
- Tier3: Knowledge/awareness variables (know, aware, familiar)
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import or_, and_
import logging
import re

from models import Variable, Dataset, Audience
from services.structured_aggregation_service import structured_aggregation_service
from services.embedding_service import embedding_service
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class DecisionProxyService:
    """Service for handling decision/normative questions with proxy ladder fallback"""
    
    def __init__(self):
        # Tier keywords for proxy ladder
        self.tier0_keywords = [
            'pref', 'choice', 'select', 'which', 'nps', 'satisfaction', 'consider', 
            'intent', 'switch', 'tercih', 'seçim', 'seçenek', 'memnuniyet', 'niyet'
        ]
        self.tier1_keywords = [
            'purchase', 'buy', 'bought', 'usage', 'use', 'frequency', 'last', 
            'satın', 'kullanım', 'kullan', 'sıklık', 'son'
        ]
        self.tier2_keywords = [
            'trust', 'value', 'quality', 'reliability', 'fit', 'important', 
            'güven', 'değer', 'kalite', 'güvenilirlik', 'uygun', 'önemli'
        ]
        self.tier3_keywords = [
            'know', 'aware', 'familiar', 'heard', 'bilgi', 'farkında', 'tanıdık', 
            'duydu', 'aşina'
        ]
    
    def build_proxy_ladder(
        self,
        db: Session,
        dataset_id: str,
        entities_in_question: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build proxy ladder: search for candidate variables grouped by tier.
        
        Returns:
            Dict with keys 'tier0', 'tier1', 'tier2', 'tier3', each containing
            list of {variable_id, var_code, label, question_text, tier, match_reason}
        """
        if not DATABASE_AVAILABLE:
            return {'tier0': [], 'tier1': [], 'tier2': [], 'tier3': []}
        
        ladder = {
            'tier0': [],
            'tier1': [],
            'tier2': [],
            'tier3': []
        }
        
        # Get all single_choice variables for this dataset
        all_variables = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            Variable.var_type == 'single_choice'
        ).all()
        
        for var in all_variables:
            # Check if has >=3 value labels
            value_labels = var.value_labels or []
            if not isinstance(value_labels, list) or len(value_labels) < 3:
                continue
            
            var_text = (var.question_text or var.label or var.code or '').lower()
            var_code_lower = (var.code or '').lower()
            combined_text = f"{var_text} {var_code_lower}"
            
            # Tier0: Direct preference/choice
            tier0_match = any(kw in combined_text for kw in self.tier0_keywords)
            if tier0_match:
                ladder['tier0'].append({
                    'variable_id': var.id,
                    'var_code': var.code,
                    'label': var.label,
                    'question_text': var.question_text,
                    'tier': 0,
                    'tier_name': 'Direct Preference/Choice',
                    'match_reason': f"Matches Tier0 keywords in {var.code}"
                })
                continue
            
            # Tier1: Behavioral
            tier1_match = any(kw in combined_text for kw in self.tier1_keywords)
            if tier1_match:
                ladder['tier1'].append({
                    'variable_id': var.id,
                    'var_code': var.code,
                    'label': var.label,
                    'question_text': var.question_text,
                    'tier': 1,
                    'tier_name': 'Behavioral',
                    'match_reason': f"Matches Tier1 keywords in {var.code}"
                })
                continue
            
            # Tier2: Attitudinal
            tier2_match = any(kw in combined_text for kw in self.tier2_keywords)
            if tier2_match:
                ladder['tier2'].append({
                    'variable_id': var.id,
                    'var_code': var.code,
                    'label': var.label,
                    'question_text': var.question_text,
                    'tier': 2,
                    'tier_name': 'Attitudinal',
                    'match_reason': f"Matches Tier2 keywords in {var.code}"
                })
                continue
            
            # Tier3: Knowledge/awareness
            tier3_match = any(kw in combined_text for kw in self.tier3_keywords)
            if tier3_match:
                ladder['tier3'].append({
                    'variable_id': var.id,
                    'var_code': var.code,
                    'label': var.label,
                    'question_text': var.question_text,
                    'tier': 3,
                    'tier_name': 'Knowledge/Awareness',
                    'match_reason': f"Matches Tier3 keywords in {var.code}"
                })
        
        # Log ladder results
        for tier_name, candidates in ladder.items():
            if candidates:
                logger.info(f"Proxy ladder {tier_name}: {len(candidates)} candidates found")
        
        return ladder
    
    def choose_best_proxy(
        self,
        db: Session,
        ladder: Dict[str, List[Dict[str, Any]]],
        dataset_id: str,
        audience_id: Optional[str] = None,
        min_base_n: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Choose best proxy from ladder, checking base_n for each candidate.
        
        Returns:
            Best candidate dict with tier info, or None if no suitable proxy found
        """
        # Try each tier in order (0 -> 1 -> 2 -> 3)
        for tier_key in ['tier0', 'tier1', 'tier2', 'tier3']:
            candidates = ladder.get(tier_key, [])
            
            for candidate in candidates:
                var_id = candidate['variable_id']
                
                # Check base_n for this variable
                try:
                    # Quick check: get distribution to see base_n
                    dist_evidence = structured_aggregation_service.aggregate_single_choice(
                        db=db,
                        variable_id=var_id,
                        dataset_id=dataset_id,
                        audience_id=audience_id,
                        negation_ast=None
                    )
                    
                    base_n = dist_evidence.get('base_n', 0)
                    if base_n >= min_base_n:
                        # Found suitable proxy
                        candidate['base_n'] = base_n
                        candidate['dataset_id'] = dataset_id
                        candidate['confidence'] = self._calculate_proxy_confidence(
                            tier=candidate['tier'],
                            base_n=base_n
                        )
                        logger.info(f"Selected proxy: {candidate['var_code']} (Tier{candidate['tier']}, N={base_n})")
                        return candidate
                except Exception as e:
                    logger.warning(f"Error checking base_n for {candidate['var_code']}: {e}")
                    continue
        
        # No suitable proxy found
        logger.warning("No suitable proxy found in ladder (all candidates have base_n < min_base_n)")
        return None
    
    def _calculate_proxy_confidence(self, tier: int, base_n: int) -> float:
        """
        Calculate confidence score based on tier and base_n.
        
        Tier0: highest confidence (0.85-0.95)
        Tier1: high confidence (0.70-0.85)
        Tier2: medium confidence (0.55-0.70)
        Tier3: low confidence (0.40-0.55)
        
        Base_n also affects: higher N = higher confidence
        """
        tier_base = {
            0: 0.90,
            1: 0.75,
            2: 0.60,
            3: 0.45
        }.get(tier, 0.50)
        
        # Adjust for base_n (N>=100 = +0.05, N>=500 = +0.10)
        n_bonus = 0.0
        if base_n >= 500:
            n_bonus = 0.10
        elif base_n >= 100:
            n_bonus = 0.05
        
        confidence = min(0.95, tier_base + n_bonus)
        return confidence
    
    def identify_proxy_target_variable(
        self,
        db: Session,
        dataset_id: str,
        question_text: str,
        router_payload: Dict[str, Any]
    ) -> Tuple[Optional[int], float, List[Dict[str, Any]]]:
        """
        Identify proxy target variable(s) for decision question.
        
        Returns:
            tuple: (variable_id, confidence_score, alternative_candidates)
            - variable_id: Best match variable ID or None
            - confidence_score: 0.0-1.0, how confident we are this is the right proxy
            - alternative_candidates: List of {variable_id, var_code, confidence, method} for top 3 alternatives
        """
        if not DATABASE_AVAILABLE:
            return None, 0.0, []
        
        candidates = []  # List of {variable_id, var_code, confidence, method}
        
        # Method 1: Check if var_code is explicitly mentioned (highest confidence)
        var_code_pattern = r'\b[A-Z][A-Z0-9_]{1,30}\b'
        potential_codes = re.findall(var_code_pattern, question_text.upper())
        
        for code in potential_codes:
            variable = db.query(Variable).filter(
                Variable.dataset_id == dataset_id,
                Variable.code == code
            ).first()
            if variable and variable.var_type == 'single_choice':
                value_labels = variable.value_labels or []
                if isinstance(value_labels, list) and len(value_labels) >= 3:
                    logger.info(f"Found proxy target variable via var_code: {code} (id: {variable.id})")
                    candidates.append({
                        'variable_id': variable.id,
                        'var_code': variable.code,
                        'confidence': 0.95,  # High confidence for explicit var_code
                        'method': 'explicit_var_code'
                    })
        
        # Method 2: Try embedding search
        try:
            query_embedding = embedding_service.generate_embedding(question_text)
            if query_embedding:
                embedding_candidates = embedding_service.get_variable_embeddings(
                    db=db,
                    dataset_id=dataset_id,
                    query_vector=query_embedding,
                    top_k=10
                )
                
                # Filter for single_choice with >=3 categories
                for candidate in embedding_candidates:
                    variable = db.query(Variable).filter(
                        Variable.id == candidate['variable_id']
                    ).first()
                    
                    if variable and variable.var_type == 'single_choice':
                        value_labels = variable.value_labels or []
                        if isinstance(value_labels, list) and len(value_labels) >= 3:
                            # Use similarity score as confidence (normalize to 0-1)
                            similarity = candidate.get('similarity', 0.0)
                            confidence = max(0.0, min(1.0, (similarity + 1) / 2))  # Normalize -1 to 1 range to 0-1
                            
                            # Check if already in candidates
                            if not any(c['variable_id'] == variable.id for c in candidates):
                                candidates.append({
                                    'variable_id': variable.id,
                                    'var_code': variable.code,
                                    'confidence': confidence,
                                    'method': 'embedding_similarity'
                                })
        except Exception as e:
            logger.warning(f"Error in embedding search for proxy target: {e}")
        
        # Method 3: Check for keywords like "plan", "option", "choice"
        normalized_q = question_text.lower()
        plan_keywords = ['plan', 'option', 'choice', 'seçenek', 'planı', 'seçim']
        
        if any(kw in normalized_q for kw in plan_keywords):
            variables = db.query(Variable).filter(
                Variable.dataset_id == dataset_id,
                Variable.var_type == 'single_choice'
            ).all()
            
            for var in variables:
                var_text = (var.question_text or var.label or var.code or '').lower()
                if any(kw in var_text for kw in plan_keywords):
                    value_labels = var.value_labels or []
                    if isinstance(value_labels, list) and len(value_labels) >= 3:
                        # Check if already in candidates
                        if not any(c['variable_id'] == var.id for c in candidates):
                            candidates.append({
                                'variable_id': var.id,
                                'var_code': var.code,
                                'confidence': 0.60,  # Medium confidence for keyword match
                                'method': 'keyword_match'
                            })
        
        # Sort by confidence and return best match + top 3 alternatives
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        if candidates:
            best = candidates[0]
            alternatives = candidates[1:4]  # Top 3 alternatives
            return best['variable_id'], best['confidence'], alternatives
        else:
            logger.warning(f"Could not identify proxy target variable for question: {question_text}")
            return None, 0.0, []
    
    def generate_decision_rules(
        self,
        distribution_evidence: Dict[str, Any],
        comparison_evidence: Optional[Dict[str, Any]] = None,
        proxy_tier: Optional[int] = None,
        auto_risk_averse: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate 2-3 assumption-based decision rules.
        
        Rules must be clearly labeled as assumptions and use ONLY computed evidence numbers.
        """
        rules = []
        
        categories = distribution_evidence.get('categories', [])
        if not categories:
            return rules
        
        base_n = distribution_evidence.get('base_n', 0)
        answered_n = distribution_evidence.get('answered_n', 0)
        
        # Get top option
        top_option = categories[0] if categories else None
        top_percent = top_option.get('percent', 0) if top_option else 0
        top_label = top_option.get('label', 'Unknown') if top_option else 'Unknown'
        
        # Rule 1: Popularity-first
        # For Tier3, add disclaimer that this measures familiarity, not preference
        assumption_text = "Best choice is what most respondents prefer in this audience."
        if proxy_tier == 3:
            assumption_text = "Best choice is what most respondents are familiar with (NOT preference). This proxy measures knowledge/awareness, not actual preference."
        
        rules.append({
            "id": "popularity_first",
            "title": "Popularity-first",
            "assumption": assumption_text,
            "how_to_apply": f"Pick top option by %valid in current audience.",
            "result_preview": {
                "top_option": top_label,
                "supporting_metric": f"{top_percent:.1f}%"
            },
            "tier_disclaimer": "⚠️ This measures familiarity, not preference." if proxy_tier == 3 else None
        })
        
        # Rule 2: Risk-averse (with automatic "gather more data" for small N)
        second_option = categories[1] if len(categories) > 1 else None
        second_percent = second_option.get('percent', 0) if second_option else 0
        gap = top_percent - second_percent
        
        # Auto-recommend "gather more data" if auto_risk_averse flag is set or base_n < 100
        if auto_risk_averse or base_n < 100:
            rules.append({
                "id": "risk_averse",
                "title": "Risk-averse",
                "assumption": "Avoid options with high uncertainty; prefer stable second-best if sample is small or polarized.",
                "how_to_apply": "If base_n < 100 or top2 gap < 5pp, recommend gathering more data; else pick top.",
                "result_preview": {
                    "recommendation": "Gather more data / widen audience",
                    "reason": f"Base n: {base_n} (too small for reliable decision)"
                }
            })
        elif gap < 5.0:
            rules.append({
                "id": "risk_averse",
                "title": "Risk-averse",
                "assumption": "Avoid options with high uncertainty; prefer stable second-best if sample is small or polarized.",
                "how_to_apply": "If base_n < 100 or top2 gap < 5pp, recommend gathering more data; else pick top.",
                "result_preview": {
                    "recommendation": "Gather more data / widen audience",
                    "reason": f"Top2 gap: {gap:.1f}pp (too close, high uncertainty)"
                }
            })
        else:
            rules.append({
                "id": "risk_averse",
                "title": "Risk-averse",
                "assumption": "Avoid options with high uncertainty; prefer stable second-best if sample is small or polarized.",
                "how_to_apply": "Pick top option since base_n >= 100 and gap >= 5pp.",
                "result_preview": {
                    "recommendation": top_label,
                    "reason": f"Base n: {base_n}, Gap: {gap:.1f}pp"
                }
            })
        
        # Rule 3: Segment-fit (if comparison evidence exists, with min thresholds)
        if comparison_evidence and comparison_evidence.get('comparison_type') == 'audience_vs_total':
            audience_cats = comparison_evidence.get('audience', {}).get('categories', [])
            total_cats = comparison_evidence.get('total', {}).get('categories', [])
            audience_base_n = comparison_evidence.get('audience', {}).get('base_n', 0)
            
            if audience_cats and total_cats:
                # Find option with max lift
                max_lift = -999
                max_lift_option = None
                
                for aud_cat in audience_cats:
                    aud_label = aud_cat.get('label', '')
                    aud_pct = aud_cat.get('percent', 0)
                    
                    # Find corresponding total
                    total_pct = 0
                    for tot_cat in total_cats:
                        if tot_cat.get('label') == aud_label:
                            total_pct = tot_cat.get('percent', 0)
                            break
                    
                    lift = aud_pct - total_pct
                    if lift > max_lift:
                        max_lift = lift
                        max_lift_option = aud_label
                
                # Apply minimum thresholds: base_n >= 100 and abs(delta_pp) >= 5pp
                if max_lift_option and audience_base_n >= 100 and abs(max_lift) >= 5.0:
                    rules.append({
                        "id": "segment_fit",
                        "title": "Segment-fit",
                        "assumption": "Best choice is the option that over-indexes vs overall sample (lift).",
                        "how_to_apply": f"Pick option with max +diff_pp in audience vs overall (min thresholds: N>=100, |delta|>=5pp).",
                        "result_preview": {
                            "top_option": max_lift_option,
                            "lift_pp": f"+{max_lift:.1f}pp"
                        }
                    })
                elif max_lift_option:
                    # Thresholds not met, but still show option with warning
                    rules.append({
                        "id": "segment_fit",
                        "title": "Segment-fit",
                        "assumption": "Best choice is the option that over-indexes vs overall sample (lift).",
                        "how_to_apply": f"Pick option with max +diff_pp in audience vs overall (min thresholds: N>=100, |delta|>=5pp).",
                        "result_preview": {
                            "top_option": max_lift_option,
                            "lift_pp": f"+{max_lift:.1f}pp",
                            "warning": f"Thresholds not met: N={audience_base_n}, |delta|={abs(max_lift):.1f}pp"
                        }
                    })
        
        # If no segment-fit rule, add a generic one
        if len(rules) < 3:
            rules.append({
                "id": "segment_fit",
                "title": "Segment-fit",
                "assumption": "Best choice is the option that over-indexes vs overall sample (lift).",
                "how_to_apply": "Requires comparison data (audience vs total).",
                "result_preview": {
                    "note": "Comparison data not available"
                }
            })
        
        return rules[:3]  # Return max 3 rules
    
    def generate_clarifying_controls(self) -> Dict[str, Any]:
        """
        Generate UI controls for decision criteria selection.
        
        Returns structure for frontend to render sliders/toggles.
        """
        return {
            "decision_goal": {
                "type": "single_select",
                "label": "What matters most?",
                "options": [
                    {"id": "cost", "label": "Cost savings"},
                    {"id": "flexibility", "label": "Flexibility / no contract"},
                    {"id": "upgrade", "label": "Device upgrade"},
                    {"id": "support", "label": "Support quality"},
                    {"id": "risk", "label": "Risk / uncertainty"}
                ],
                "default": "cost"
            },
            "confidence_threshold": {
                "type": "slider",
                "label": "Minimum confidence required",
                "min": 0,
                "max": 100,
                "step": 5,
                "default": 60
            }
        }
    
    def generate_next_best_questions(
        self,
        db: Session,
        target_variable_id: Optional[int],
        dataset_id: str,
        audience_id: Optional[str],
        question_text: str,
        proxy_tier: Optional[int] = None,
        proxy_copy: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate 5-8 follow-up questions that make the answer measurable.
        
        These must be phrased so they can be routed to structured/rag.
        IMPORTANT: Only suggest questions for variables/types that exist in the dataset.
        """
        questions = []
        
        # Use follow_up_templates from proxy_copy if available
        if proxy_copy and proxy_copy.get('follow_up_templates'):
            templates = proxy_copy['follow_up_templates']
            var_code = None
            if target_variable_id:
                variable = db.query(Variable).filter(Variable.id == target_variable_id).first()
                var_code = variable.code if variable else None
            
            # Replace placeholders in templates
            for template in templates[:5]:  # Max 5 from templates
                question = template
                if var_code:
                    question = question.replace('{var_code}', var_code)
                if audience_id:
                    question = question.replace('{audience}', 'this audience')
                # Placeholder replacements for brands (could be extracted from question_text)
                question = question.replace('{brand_a}', 'option A')
                question = question.replace('{brand_b}', 'option B')
                questions.append(question)
        
        # Build ladder to suggest questions from higher tiers
        ladder = self.build_proxy_ladder(db=db, dataset_id=dataset_id)
        
        # If proxy_tier is set, suggest questions from higher tiers (preference > consideration > attitudes > knowledge)
        if proxy_tier is not None and proxy_tier >= 0:
            # Suggest from tier above current proxy
            for tier_offset in range(1, 4):  # Try tier-1, tier-2, tier-3 above
                target_tier = proxy_tier - tier_offset
                if target_tier < 0:
                    break
                
                tier_key = f'tier{target_tier}'
                tier_candidates = ladder.get(tier_key, [])
                if tier_candidates:
                    var_code = tier_candidates[0]['var_code']
                    questions.append(f"What is the distribution of {var_code}?")
                    if len(questions) >= 8:  # Total max 8
                        break
        
        # Check if dataset has open-end/verbatim variables (for RAG questions)
        has_open_end = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            Variable.var_type.in_(['text', 'open_end', 'verbatim'])
        ).first() is not None
        
        if target_variable_id:
            variable = db.query(Variable).filter(Variable.id == target_variable_id).first()
            var_code = variable.code if variable else "target variable"
            
            questions.extend([
                f"What is the distribution of {var_code} in the total sample?",
                f"Compare {var_code} for this audience vs total.",
                f"Which segment over-indexes for {var_code}?",
            ])
            
            # Check if price sensitivity variable exists
            price_sensitivity_vars = db.query(Variable).filter(
                Variable.dataset_id == dataset_id,
                Variable.var_type == 'single_choice',
                or_(
                    Variable.label.ilike('%price%'),
                    Variable.label.ilike('%cost%'),
                    Variable.label.ilike('%fiyat%'),
                    Variable.label.ilike('%maliyet%')
                )
            ).first()
            
            if price_sensitivity_vars and audience_id:
                questions.append(f"Among those who chose the top option in {var_code}, what is their price sensitivity distribution?")
        
        # Only suggest open-end questions if dataset has open-end variables
        if has_open_end:
            questions.append("What are the top reasons mentioned by respondents who chose the most popular option?")
        
        # Check if age group variable exists
        age_vars = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            or_(
                Variable.code.ilike('%AGE%'),
                Variable.code.ilike('%D1%'),
                Variable.label.ilike('%age%'),
                Variable.label.ilike('%yaş%')
            )
        ).first()
        
        if age_vars:
            questions.append("What is the breakdown of plan choice by age group?")
        
        # Demographic comparison question (if demographics exist)
        demo_vars = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            Variable.var_type == 'single_choice',
            or_(
                Variable.label.ilike('%gender%'),
                Variable.label.ilike('%cinsiyet%'),
                Variable.label.ilike('%region%'),
                Variable.label.ilike('%bölge%')
            )
        ).first()
        
        if demo_vars:
            questions.append("Compare plan preference between different demographic segments.")
        
        # Satisfaction/NPS question (if satisfaction variables exist)
        satisfaction_vars = db.query(Variable).filter(
            Variable.dataset_id == dataset_id,
            or_(
                Variable.label.ilike('%satisfaction%'),
                Variable.label.ilike('%NPS%'),
                Variable.label.ilike('%memnuniyet%'),
                Variable.label.ilike('%rating%')
            )
        ).first()
        
        if satisfaction_vars:
            questions.append("What is the correlation between plan choice and satisfaction scores?")
        
        return questions[:8]  # Return max 8 questions
    
    async def answer_decision_question(
        self,
        db: Session,
        dataset_id: str,
        audience_id: Optional[str],
        question_text: str,
        router_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Answer a decision/normative question with data-backed proxy and assumption-based rules.
        
        Returns:
            Dict with:
                - mode: "decision_proxy"
                - proxy_answer: data-backed sections
                - decision_rules: assumption-based rules
                - clarifying_controls: UI controls
                - next_best_questions: follow-up questions
                - evidence_json: underlying evidence
                - citations_json: only if RAG/open-ends used
                - debug_json: mapping and logic
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        debug_json = {
            "question_text": question_text,
            "dataset_id": dataset_id,
            "audience_id": audience_id,
            "router_payload": router_payload
        }
        
        # Step 1: Identify proxy target variable using ladder fallback
        # First try explicit/embedding methods
        proxy_target_variable_id, proxy_confidence, alternative_candidates = self.identify_proxy_target_variable(
            db=db,
            dataset_id=dataset_id,
            question_text=question_text,
            router_payload=router_payload
        )
        
        proxy_tier = None
        proxy_tier_name = None
        proxy_var_code = None
        proxy_question_text = None
        proxy_reason = None
        
        # If no explicit match found, use proxy ladder
        if not proxy_target_variable_id:
            logger.info("No explicit proxy found, building proxy ladder...")
            ladder = self.build_proxy_ladder(
                db=db,
                dataset_id=dataset_id,
                entities_in_question=None  # Could extract entities from question_text
            )
            
            best_proxy = self.choose_best_proxy(
                db=db,
                ladder=ladder,
                dataset_id=dataset_id,
                audience_id=audience_id,
                min_base_n=30
            )
            
            if best_proxy:
                proxy_target_variable_id = best_proxy['variable_id']
                proxy_confidence = best_proxy.get('confidence', 0.5)
                proxy_tier = best_proxy['tier']
                proxy_tier_name = best_proxy['tier_name']
                proxy_var_code = best_proxy['var_code']
                proxy_question_text = best_proxy.get('question_text')
                proxy_reason = best_proxy.get('match_reason', 'Proxy ladder match')
                
                # Build alternatives from ladder
                alternative_candidates = []
                for tier_key in ['tier0', 'tier1', 'tier2', 'tier3']:
                    for alt in ladder.get(tier_key, [])[:2]:  # Top 2 per tier
                        if alt['variable_id'] != proxy_target_variable_id:
                            alternative_candidates.append({
                                'var_code': alt['var_code'],
                                'confidence': self._calculate_proxy_confidence(alt['tier'], alt.get('base_n', 0)),
                                'method': f"Tier{alt['tier']} ladder",
                                'tier': alt['tier'],
                                'tier_name': alt['tier_name']
                            })
                alternative_candidates = alternative_candidates[:5]  # Top 5 total
        
        # Get proxy variable info if found via explicit method
        if proxy_target_variable_id and not proxy_tier:
            proxy_var = db.query(Variable).filter(Variable.id == proxy_target_variable_id).first()
            if proxy_var:
                proxy_var_code = proxy_var.code
                proxy_question_text = proxy_var.question_text
                
                # Determine tier from variable content
                var_text = (proxy_var.question_text or proxy_var.label or proxy_var.code or '').lower()
                if any(kw in var_text for kw in self.tier0_keywords):
                    proxy_tier = 0
                    proxy_tier_name = 'Direct Preference/Choice'
                elif any(kw in var_text for kw in self.tier1_keywords):
                    proxy_tier = 1
                    proxy_tier_name = 'Behavioral'
                elif any(kw in var_text for kw in self.tier2_keywords):
                    proxy_tier = 2
                    proxy_tier_name = 'Attitudinal'
                elif any(kw in var_text for kw in self.tier3_keywords):
                    proxy_tier = 3
                    proxy_tier_name = 'Knowledge/Awareness'
                else:
                    proxy_tier = 3  # Default to Tier3 if unclear
                    proxy_tier_name = 'Knowledge/Awareness'
                
                proxy_reason = "Explicit/embedding match"
        
        debug_json["proxy_target_variable_id"] = proxy_target_variable_id
        debug_json["proxy_confidence"] = proxy_confidence
        debug_json["proxy_var_code"] = proxy_var_code
        debug_json["proxy_tier"] = proxy_tier
        debug_json["proxy_tier_name"] = proxy_tier_name
        debug_json["alternative_candidates"] = alternative_candidates
        
        # Step 2: Build proxy_answer (DATA ONLY)
        # Note: proxy_copy will be added after severity determination
        proxy_answer = {
            "what_we_can_measure": [],
            "what_we_cannot_measure": [],
            "proxy_header": {
                "is_proxy": True,
                "message": "Not directly measured → using proxy",
                "proxy_var_code": proxy_var_code,
                "proxy_question_text": proxy_question_text,
                "tier": proxy_tier,
                "tier_name": proxy_tier_name,
                "confidence": round(proxy_confidence, 2),
                "reason": proxy_reason,
                "alternatives": [
                    {
                        "var_code": alt.get('var_code'),
                        "confidence": round(alt.get('confidence', 0.0), 2),
                        "method": alt.get('method'),
                        "tier": alt.get('tier'),
                        "tier_name": alt.get('tier_name')
                    }
                    for alt in alternative_candidates[:3]
                ]
            } if proxy_target_variable_id else {
                "is_proxy": False,
                "message": "Could not identify a proxy variable for this question",
                "what_we_cannot_measure": [
                    "Direct preference/choice data",
                    "Consideration intent",
                    "Purchase behavior",
                    "Attitudinal measures"
                ]
            }
        }
        
        evidence_json = {
            "mode": "decision_proxy",
            "distribution": None,
            "comparison": None,
            "drivers": None
        }
        
        if proxy_target_variable_id:
            # Get distribution evidence
            try:
                distribution_evidence = structured_aggregation_service.aggregate_single_choice(
                    db=db,
                    variable_id=proxy_target_variable_id,
                    dataset_id=dataset_id,
                    audience_id=audience_id,
                    negation_ast=None
                )
                
                evidence_json["distribution"] = distribution_evidence
                
                proxy_answer["what_we_can_measure"].append({
                    "type": "distribution",
                    "title": f"Distribution of choices in {'audience' if audience_id else 'total sample'}",
                    "evidence_ref": "distribution"
                })
                
                debug_json["distribution_computed"] = True
            except Exception as e:
                logger.error(f"Error computing distribution: {e}", exc_info=True)
                debug_json["distribution_error"] = str(e)
            
            # Get comparison evidence (if audience exists)
            if audience_id:
                try:
                    comparison_evidence = structured_aggregation_service.compare_audience_vs_total(
                        db=db,
                        variable_id=proxy_target_variable_id,
                        audience_id=audience_id,
                        dataset_id=dataset_id,
                        negation_ast=None
                    )
                    
                    evidence_json["comparison"] = comparison_evidence
                    
                    # Calculate delta_pp
                    audience_cats = comparison_evidence.get('audience', {}).get('categories', [])
                    total_cats = comparison_evidence.get('total', {}).get('categories', [])
                    
                    delta_pp = []
                    for aud_cat in audience_cats:
                        aud_label = aud_cat.get('label', '')
                        aud_pct = aud_cat.get('percent', 0)
                        
                        total_pct = 0
                        for tot_cat in total_cats:
                            if tot_cat.get('label') == aud_label:
                                total_pct = tot_cat.get('percent', 0)
                                break
                        
                        delta_pp.append({
                            "option": aud_label,
                            "audience_percent": aud_pct,
                            "overall_percent": total_pct,
                            "diff_pp": round(aud_pct - total_pct, 2)
                        })
                    
                    evidence_json["comparison"]["delta_pp"] = delta_pp
                    
                    proxy_answer["what_we_can_measure"].append({
                        "type": "segment_comparison",
                        "title": "Audience vs total sample comparison",
                        "evidence_ref": "comparison"
                    })
                    
                    debug_json["comparison_computed"] = True
                except Exception as e:
                    logger.error(f"Error computing comparison: {e}", exc_info=True)
                    debug_json["comparison_error"] = str(e)
                    comparison_evidence = None
            else:
                comparison_evidence = None
            
            # Drivers analysis (optional - skip for now, can be added later)
            proxy_answer["what_we_can_measure"].append({
                "type": "drivers",
                "title": "Drivers not available in this dataset",
                "evidence_ref": None,
                "note": "Driver analysis requires additional variables (price sensitivity, trust, etc.)"
            })
        else:
            # No target variable found
            proxy_answer["what_we_can_measure"].append({
                "type": "note",
                "title": "Could not identify a target variable for this decision question",
                "evidence_ref": None
            })
            distribution_evidence = {}
            comparison_evidence = None
        
        # Step 3: Determine severity and get proxy copy
        base_n = distribution_evidence.get('base_n', 0) if distribution_evidence else 0
        top2_gap_pp = 0.0
        if distribution_evidence and distribution_evidence.get('categories'):
            categories = distribution_evidence['categories']
            if len(categories) >= 2:
                top1_pct = categories[0].get('percent', 0)
                top2_pct = categories[1].get('percent', 0)
                top2_gap_pp = top1_pct - top2_pct
        
        # Determine severity based on tier, confidence, base_n, gap
        severity = 'info'
        if proxy_tier == 3:
            severity = 'risk'
        elif proxy_tier == 2:
            if base_n < 100 or top2_gap_pp < 5.0 or proxy_confidence < 0.55:
                severity = 'risk'
            else:
                severity = 'warn'
        elif proxy_tier == 1:
            if base_n < 100 or top2_gap_pp < 5.0 or proxy_confidence < 0.70:
                severity = 'warn'
        elif proxy_tier == 0:
            if base_n < 100 or top2_gap_pp < 5.0 or proxy_confidence < 0.85:
                severity = 'warn'
        
        low_confidence_flag = (
            base_n < 100 or 
            top2_gap_pp < 5.0 or 
            (proxy_tier == 0 and proxy_confidence < 0.85) or
            (proxy_tier == 1 and proxy_confidence < 0.70) or
            (proxy_tier == 2 and proxy_confidence < 0.55) or
            proxy_tier == 3
        )
        
        # Get proxy copy (default to 'en' for now, can be made configurable)
        proxy_copy = None
        if proxy_target_variable_id:
            proxy_copy = self.get_proxy_copy(
                tier=proxy_tier if proxy_tier is not None else 3,
                locale='en',  # TODO: Get from request/user preference
                severity=severity,
                low_confidence_flag=low_confidence_flag,
                base_n=base_n,
                top2_gap_pp=top2_gap_pp
            )
            # Add proxy_copy to proxy_answer
            proxy_answer["proxy_copy"] = proxy_copy
            proxy_answer["what_we_cannot_measure"] = proxy_copy.get('what_we_cannot_claim', [])
        
        # Step 4: Generate decision rules (ASSUMPTION-BASED)
        # Auto-select risk-averse if policy says so
        decision_rules = self.generate_decision_rules(
            distribution_evidence=distribution_evidence if proxy_target_variable_id else {},
            comparison_evidence=comparison_evidence,
            proxy_tier=proxy_tier,
            auto_risk_averse=proxy_copy.get('auto_risk_averse', False) if proxy_copy else False
        )
        
        # Step 5: Generate clarifying controls
        clarifying_controls = self.generate_clarifying_controls()
        
        # Step 6: Generate next best questions (dataset-aware, via ladder + templates)
        next_best_questions = self.generate_next_best_questions(
            db=db,
            target_variable_id=proxy_target_variable_id,
            dataset_id=dataset_id,
            audience_id=audience_id,
            question_text=question_text,
            proxy_tier=proxy_tier,
            proxy_copy=proxy_copy if proxy_target_variable_id else None
        )
        
        # If no proxy found, still generate questions from ladder
        if not proxy_target_variable_id:
            ladder = self.build_proxy_ladder(db=db, dataset_id=dataset_id)
            # Suggest questions from available tiers
            for tier_key in ['tier0', 'tier1', 'tier2', 'tier3']:
                tier_candidates = ladder.get(tier_key, [])
                if tier_candidates:
                    var_code = tier_candidates[0]['var_code']
                    next_best_questions.append(f"What is the distribution of {var_code}?")
                    if len(next_best_questions) >= 5:
                        break
        
        # Build narrative text (SAFE formatter, no LLM)
        # IMPORTANT: Start with clear proxy disclaimer
        narrative_parts = []
        
        if proxy_target_variable_id:
            tier_label = proxy_tier_name or f"Tier{proxy_tier}" if proxy_tier is not None else "Unknown"
            narrative_parts.append(
                f"⚠️ Sorunuz bu veri setinde doğrudan ölçülmüyor. "
                f"Proxy değişken kullanılıyor: {proxy_var_code} ({tier_label}, güven: %{proxy_confidence:.0f})."
            )
            
            # Stronger warning for Tier3
            if proxy_tier == 3:
                narrative_parts.append(
                    "⚠️ UYARI: Bu proxy bilgi/farkındalığı ölçer, tercihi DEĞİL. "
                    "Tanıdıklık tercih anlamına gelmez."
                )
            
            if alternative_candidates:
                alt_codes = [alt.get('var_code') for alt in alternative_candidates[:2]]
                if alt_codes:
                    narrative_parts.append(f"Alternatif proxy'ler: {', '.join(alt_codes)}.")
        
        narrative_parts.append("Ölçebildiklerimiz:")
        
        # Add "what we cannot measure" if applicable
        if proxy_answer.get("what_we_cannot_measure"):
            narrative_parts.append(
                f"Ölçülemez: {', '.join(proxy_answer['what_we_cannot_measure'])}."
            )
        
        if proxy_target_variable_id and distribution_evidence:
            categories = distribution_evidence.get('categories', [])
            base_n = distribution_evidence.get('base_n', 0)
            answered_n = distribution_evidence.get('answered_n', 0)
            
            if categories:
                top_cat = categories[0]
                narrative_parts.append(
                    f"Dağılım: '{top_cat.get('label')}' katılımcıların %{top_cat.get('percent', 0):.1f}'i tarafından seçildi "
                    f"({answered_n} kişiden {top_cat.get('count', 0)} kişi, temel N={base_n})."
                )
        
        if comparison_evidence and evidence_json.get("comparison", {}).get("delta_pp"):
            delta_pp = evidence_json["comparison"]["delta_pp"]
            if delta_pp:
                max_lift = max(delta_pp, key=lambda x: x.get('diff_pp', 0))
                narrative_parts.append(
                    f"Karşılaştırma: '{max_lift.get('option')}' toplam örneğe göre {max_lift.get('diff_pp', 0):+.1f} yüzde puanı "
                    f"fark gösteriyor."
                )
        
        narrative_parts.append(
            "Karar vermek için lütfen aşağıdan bir karar kuralı seçin. "
            "Her kural, bir seçimin 'en iyi' olmasını sağlayan şey hakkında farklı bir varsayımı temsil eder."
        )
        
        narrative_text = " ".join(narrative_parts) if narrative_parts else (
            "Bu karar odaklı bir sorudur. Lütfen bir öneri görmek için bir karar kuralı seçin."
        )
        
        return {
            "mode": "decision_proxy",
            "proxy_answer": proxy_answer,
            "decision_rules": decision_rules,
            "clarifying_controls": clarifying_controls,
            "next_best_questions": next_best_questions,
            "evidence_json": evidence_json,
            "citations_json": [],  # No RAG citations for decision_proxy
            "debug_json": debug_json,
            "narrative_text": narrative_text
        }


    def get_proxy_copy(
        self,
        tier: int,
        locale: str = 'en',
        severity: str = 'info',
        low_confidence_flag: bool = False,
        base_n: int = 0,
        top2_gap_pp: float = 0.0
    ) -> Dict[str, Any]:
        """
        Get proxy copy pack for given tier and conditions.
        
        Returns:
            Dict with banner_title, limitation_statement, what_we_can_measure,
            what_we_cannot_claim, follow_up_templates, severity, auto_risk_averse
        """
        # Determine auto_risk_averse
        auto_risk_averse = (
            base_n < 100 or 
            top2_gap_pp < 5.0 or 
            severity == 'risk'
        )
        
        # Copy packs (Tier0-3, EN/TR)
        COPY_PACKS = {
            'en': {
                0: {
                    'tier_name': 'Direct Preference/Choice',
                    'banner_title': 'Direct preference measure available',
                    'limitation_statement': 'This measures stated preference directly from the dataset.',
                    'what_we_can_measure': 'Preference distribution and segment differences',
                    'what_we_cannot_claim': [
                        'Actual purchase behavior (stated ≠ revealed preference)',
                        'Long-term loyalty or switching intent'
                    ],
                    'follow_up_templates': [
                        'What drives preference for {var_code}?',
                        'Compare {var_code} preference between {audience} and total sample',
                        'Which segments over-index for the top choice in {var_code}?',
                        'What is the correlation between {var_code} and satisfaction scores?'
                    ]
                },
                1: {
                    'tier_name': 'Behavioral',
                    'banner_title': 'Using intent/consideration as preference proxy',
                    'limitation_statement': 'This measures purchase intent or consideration, which correlates with but is not identical to preference.',
                    'what_we_can_measure': 'Intent distribution, consideration set, satisfaction scores',
                    'what_we_cannot_claim': [
                        'Direct preference ranking (intent ≠ preference)',
                        'Purchase probability without additional context'
                    ],
                    'follow_up_templates': [
                        'What is the distribution of preference for {var_code}?',
                        'Compare consideration set between {audience} and total',
                        'Which factors drive intent for {brand_a} vs {brand_b}?',
                        'What is the correlation between intent and actual purchase behavior?'
                    ]
                },
                2: {
                    'tier_name': 'Attitudinal',
                    'banner_title': 'Using attribute perceptions as preference proxy',
                    'limitation_statement': 'This measures attribute perceptions (trust, value, quality) that may influence preference but do not directly measure it.',
                    'what_we_can_measure': 'Attribute scores, driver importance, perceived quality',
                    'what_we_cannot_claim': [
                        'Direct preference or choice (attributes ≠ preference)',
                        'Which option respondents would actually choose'
                    ],
                    'follow_up_templates': [
                        'What is the distribution of preference/choice for {var_code}?',
                        'Compare attribute perceptions between {audience} and total',
                        'Which attributes drive preference for {brand_a}?',
                        'What is the correlation between {var_code} and purchase intent?'
                    ]
                },
                3: {
                    'tier_name': 'Knowledge/Awareness',
                    'banner_title': 'Using awareness/knowledge as preference proxy',
                    'limitation_statement': '⚠️ WARNING: This measures familiarity/knowledge, NOT preference. Familiarity does not equal preference.',
                    'what_we_can_measure': 'Awareness levels, knowledge distribution, familiarity scores',
                    'what_we_cannot_claim': [
                        'Preference or choice (awareness ≠ preference)',
                        'Purchase intent or consideration',
                        'Which option respondents prefer or would choose'
                    ],
                    'follow_up_templates': [
                        'What is the distribution of preference/choice for {var_code}?',
                        'Compare preference between {audience} and total sample',
                        'What drives preference for {brand_a} vs {brand_b}?',
                        'What is the consideration set for {var_code}?',
                        'Which segments prefer {var_code}?'
                    ]
                }
            },
            'tr': {
                0: {
                    'tier_name': 'Doğrudan Tercih/Seçim',
                    'banner_title': 'Doğrudan tercih ölçümü mevcut',
                    'limitation_statement': 'Bu, veri setinden doğrudan belirtilen tercihi ölçer.',
                    'what_we_can_measure': 'Tercih dağılımı ve segment farkları',
                    'what_we_cannot_claim': [
                        'Gerçek satın alma davranışı (belirtilen ≠ gerçek tercih)',
                        'Uzun vadeli sadakat veya değiştirme niyeti'
                    ],
                    'follow_up_templates': [
                        '{var_code} için tercihi ne belirliyor?',
                        '{var_code} tercihini {audience} ve toplam örnek arasında karşılaştır',
                        'Hangi segmentler {var_code}\'da en çok seçilen seçenek için fazla endeksleniyor?',
                        '{var_code} ile memnuniyet skorları arasındaki korelasyon nedir?'
                    ]
                },
                1: {
                    'tier_name': 'Davranışsal',
                    'banner_title': 'Niyet/değerlendirme tercih proxy\'si olarak kullanılıyor',
                    'limitation_statement': 'Bu, satın alma niyetini veya değerlendirmeyi ölçer; tercihle korelasyon gösterir ancak özdeş değildir.',
                    'what_we_can_measure': 'Niyet dağılımı, değerlendirme seti, memnuniyet skorları',
                    'what_we_cannot_claim': [
                        'Doğrudan tercih sıralaması (niyet ≠ tercih)',
                        'Ek bağlam olmadan satın alma olasılığı'
                    ],
                    'follow_up_templates': [
                        '{var_code} için tercih dağılımı nedir?',
                        'Değerlendirme setini {audience} ve toplam arasında karşılaştır',
                        '{brand_a} vs {brand_b} için niyeti ne belirliyor?',
                        'Niyet ile gerçek satın alma davranışı arasındaki korelasyon nedir?'
                    ]
                },
                2: {
                    'tier_name': 'Tutumsal',
                    'banner_title': 'Özellik algıları tercih proxy\'si olarak kullanılıyor',
                    'limitation_statement': 'Bu, tercihi etkileyebilecek özellik algılarını (güven, değer, kalite) ölçer ancak tercihi doğrudan ölçmez.',
                    'what_we_can_measure': 'Özellik skorları, belirleyici önem, algılanan kalite',
                    'what_we_cannot_claim': [
                        'Doğrudan tercih veya seçim (özellikler ≠ tercih)',
                        'Katılımcıların gerçekte hangi seçeneği seçeceği'
                    ],
                    'follow_up_templates': [
                        '{var_code} için tercih/seçim dağılımı nedir?',
                        'Özellik algılarını {audience} ve toplam arasında karşılaştır',
                        'Hangi özellikler {brand_a} için tercihi belirliyor?',
                        '{var_code} ile satın alma niyeti arasındaki korelasyon nedir?'
                    ]
                },
                3: {
                    'tier_name': 'Bilgi/Farkındalık',
                    'banner_title': 'Farkındalık/bilgi tercih proxy\'si olarak kullanılıyor',
                    'limitation_statement': '⚠️ UYARI: Bu, tanıdıklık/bilgiyi ölçer, tercihi DEĞİL. Tanıdıklık tercih anlamına gelmez.',
                    'what_we_can_measure': 'Farkındalık seviyeleri, bilgi dağılımı, tanıdıklık skorları',
                    'what_we_cannot_claim': [
                        'Tercih veya seçim (farkındalık ≠ tercih)',
                        'Satın alma niyeti veya değerlendirme',
                        'Katılımcıların tercih ettiği veya seçeceği seçenek'
                    ],
                    'follow_up_templates': [
                        '{var_code} için tercih/seçim dağılımı nedir?',
                        'Tercihi {audience} ve toplam örnek arasında karşılaştır',
                        '{brand_a} vs {brand_b} için tercihi ne belirliyor?',
                        '{var_code} için değerlendirme seti nedir?',
                        'Hangi segmentler {var_code}\'u tercih ediyor?'
                    ]
                }
            }
        }
        
        # Get copy pack
        copy_pack = COPY_PACKS.get(locale, COPY_PACKS['en']).get(tier, COPY_PACKS['en'][3])
        
        # Append low confidence suffix if flag is True
        limitation = copy_pack['limitation_statement']
        if low_confidence_flag:
            if locale == 'en':
                limitation += ' (Low confidence due to small sample or close results)'
            else:
                limitation += ' (Küçük örnek veya yakın sonuçlar nedeniyle düşük güven)'
        
        return {
            'tier': tier,
            'tier_name': copy_pack['tier_name'],
            'banner_title': copy_pack['banner_title'],
            'limitation_statement': limitation,
            'what_we_can_measure': copy_pack['what_we_can_measure'],
            'what_we_cannot_claim': copy_pack['what_we_cannot_claim'],
            'follow_up_templates': copy_pack['follow_up_templates'],
            'severity': severity,
            'low_confidence_flag': low_confidence_flag,
            'auto_risk_averse': auto_risk_averse
        }


# Singleton instance
decision_proxy_service = DecisionProxyService()

