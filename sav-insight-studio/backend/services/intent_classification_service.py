"""
Intent Classification Service
Uses sentence transformers (sup-simcse-roberta-large) for semantic intent detection
Specifically for decision/normative question detection
"""
from typing import Dict, Any, Optional, List
import logging
import numpy as np

logger = logging.getLogger(__name__)


class IntentClassificationService:
    """Service for classifying question intent using sentence transformers"""
    
    def __init__(self):
        self.model = None
        self.model_name = "princeton-nlp/sup-simcse-roberta-large"
        self._intent_prototypes = None
        
    def _ensure_model(self):
        """Lazy load the sentence transformer model"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading intent classification model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("Intent classification model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers package not installed. Install with: pip install sentence-transformers")
                raise ImportError("sentence-transformers package is required for intent classification")
            except Exception as e:
                logger.error(f"Error loading intent classification model: {e}", exc_info=True)
                raise
    
    def _get_decision_intent_prototypes(self) -> List[str]:
        """
        Get prototype sentences for decision/normative intent
        These are used to compute similarity with user questions
        """
        return [
            # English decision patterns
            "which option is best",
            "what is the best choice",
            "should I choose",
            "which one should I pick",
            "what is the most logical option",
            "which plan is optimal",
            "recommend the best option",
            "what is worth it",
            "which decision should I make",
            "what is the recommended choice",
            "which option is most logical",
            "what should I select",
            "which is the better option",
            "what is the optimal choice",
            "which one is worth choosing",
            
            # Turkish decision patterns
            "hangisini seçmeli",
            "en iyi seçenek hangisi",
            "hangisi daha mantıklı",
            "hangi planı seçmeliyim",
            "önerilen seçenek hangisi",
            "hangisi daha iyi",
            "optimal seçenek hangisi",
            "hangi kararı vermeliyim",
            "tavsiye edilen seçenek",
            "hangisi değer",
            "en mantıklı seçim",
            "hangi seçeneği seçmeli",
            "hangisi daha uygun",
            "en iyi tercih hangisi",
        ]
    
    def _get_intent_prototypes(self) -> Dict[str, List[str]]:
        """
        Get prototype sentences for different intent types
        Returns dict with intent_type -> list of prototype sentences
        """
        if self._intent_prototypes is None:
            self._intent_prototypes = {
                "decision": self._get_decision_intent_prototypes(),
                "structured": [
                    "what is the distribution",
                    "how many people chose",
                    "what percentage selected",
                    "show me the counts",
                    "what is the frequency",
                    "dağılım nedir",
                    "kaç kişi seçti",
                    "yüzde kaç",
                ],
                "rag": [
                    "why did they choose",
                    "what are the reasons",
                    "explain the motivations",
                    "what feedback did they give",
                    "neden seçtiler",
                    "sebepleri neler",
                    "gerekçeleri açıkla",
                ]
            }
        return self._intent_prototypes
    
    def _compute_prototype_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Pre-compute embeddings for intent prototypes
        Returns dict with intent_type -> average embedding vector
        """
        self._ensure_model()
        prototypes = self._get_intent_prototypes()
        
        prototype_embeddings = {}
        for intent_type, sentences in prototypes.items():
            # Encode all prototype sentences
            embeddings = self.model.encode(sentences, convert_to_numpy=True)
            # Average the embeddings to get a single prototype vector
            prototype_embeddings[intent_type] = np.mean(embeddings, axis=0)
            logger.debug(f"Computed prototype embedding for intent: {intent_type} (from {len(sentences)} examples)")
        
        return prototype_embeddings
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    
    def detect_decision_intent(
        self,
        question_text: str,
        threshold: float = 0.65
    ) -> Dict[str, Any]:
        """
        Detect if question has decision/normative intent using embedding similarity
        
        Args:
            question_text: User question
            threshold: Similarity threshold (0.0-1.0). Higher = more strict.
                      Default 0.65 means 65% similarity required.
        
        Returns:
            Dict with:
                - has_decision_intent: bool
                - similarity_score: float (0.0-1.0)
                - matched_keywords: List[str] (if keyword-based also detected)
                - method: str ("embedding" or "keyword" or "both")
        """
        if not question_text or not question_text.strip():
            return {
                "has_decision_intent": False,
                "similarity_score": 0.0,
                "matched_keywords": [],
                "method": "none",
                "reason": "Empty question"
            }
        
        # First check keyword-based (fast, deterministic)
        keyword_matches = self._detect_decision_keywords(question_text)
        has_keyword_match = len(keyword_matches) > 0
        
        # Then check embedding-based (slower but more semantic)
        try:
            self._ensure_model()
            
            # Get prototype embeddings
            prototypes = self._compute_prototype_embeddings()
            decision_prototype = prototypes.get("decision")
            
            if decision_prototype is None:
                logger.warning("Decision prototype embedding not available, falling back to keyword-only")
                return {
                    "has_decision_intent": has_keyword_match,
                    "similarity_score": 0.0,
                    "matched_keywords": keyword_matches,
                    "method": "keyword" if has_keyword_match else "none",
                    "reason": "Embedding model not available"
                }
            
            # Encode question
            question_embedding = self.model.encode(question_text, convert_to_numpy=True)
            
            # Compute similarity
            similarity = self.cosine_similarity(question_embedding, decision_prototype)
            
            # Decision: use embedding similarity OR keyword match
            has_decision_intent = similarity >= threshold or has_keyword_match
            
            method = "both" if (similarity >= threshold and has_keyword_match) else \
                     ("embedding" if similarity >= threshold else "keyword" if has_keyword_match else "none")
            
            return {
                "has_decision_intent": has_decision_intent,
                "similarity_score": float(similarity),
                "matched_keywords": keyword_matches,
                "method": method,
                "threshold_used": threshold,
                "reason": f"Similarity: {similarity:.3f}, Keywords: {len(keyword_matches)}"
            }
            
        except Exception as e:
            logger.error(f"Error in embedding-based intent detection: {e}", exc_info=True)
            # Fallback to keyword-only
            return {
                "has_decision_intent": has_keyword_match,
                "similarity_score": 0.0,
                "matched_keywords": keyword_matches,
                "method": "keyword" if has_keyword_match else "none",
                "reason": f"Embedding error: {str(e)}, falling back to keywords"
            }
    
    def _detect_decision_keywords(self, question_text: str) -> List[str]:
        """
        Keyword-based decision intent detection (fallback)
        Returns list of matched keywords
        """
        normalized = question_text.lower()
        
        decision_keywords = [
            # English
            "best", "should", "most logical", "recommend", "optimal", "worth it",
            "which option", "choose", "decision", "pick", "select", "prefer",
            "better", "worse", "advice", "suggestion", "tavsiye",
            # Turkish
            "en iyi", "hangisini seçmeli", "mantıklı", "öner", "tavsiye",
            "optimal", "değer mi", "karar", "seçim", "hangi seçenek",
            "hangisi", "daha iyi", "daha kötü", "öneri"
        ]
        
        matched = []
        for keyword in decision_keywords:
            if keyword in normalized:
                matched.append(keyword)
        
        return matched
    
    def classify_intent(
        self,
        question_text: str,
        decision_threshold: float = 0.65,
        structured_threshold: float = 0.60,
        rag_threshold: float = 0.60
    ) -> Dict[str, Any]:
        """
        Classify question intent into decision/structured/rag
        
        Args:
            question_text: User question
            decision_threshold: Threshold for decision intent
            structured_threshold: Threshold for structured intent
            rag_threshold: Threshold for RAG intent
        
        Returns:
            Dict with:
                - primary_intent: str ("decision", "structured", "rag", or "unknown")
                - scores: Dict[str, float] (similarity scores for each intent)
                - confidence: float (highest score)
        """
        if not question_text or not question_text.strip():
            return {
                "primary_intent": "unknown",
                "scores": {},
                "confidence": 0.0,
                "reason": "Empty question"
            }
        
        try:
            self._ensure_model()
            prototypes = self._compute_prototype_embeddings()
            
            # Encode question
            question_embedding = self.model.encode(question_text, convert_to_numpy=True)
            
            # Compute similarities with all intent prototypes
            scores = {}
            for intent_type, prototype_embedding in prototypes.items():
                similarity = self.cosine_similarity(question_embedding, prototype_embedding)
                scores[intent_type] = float(similarity)
            
            # Determine primary intent based on thresholds and scores
            primary_intent = "unknown"
            confidence = 0.0
            
            # Check decision first (highest priority if above threshold)
            if scores.get("decision", 0.0) >= decision_threshold:
                primary_intent = "decision"
                confidence = scores["decision"]
            # Then structured
            elif scores.get("structured", 0.0) >= structured_threshold:
                primary_intent = "structured"
                confidence = scores["structured"]
            # Then RAG
            elif scores.get("rag", 0.0) >= rag_threshold:
                primary_intent = "rag"
                confidence = scores["rag"]
            # Otherwise, pick highest score even if below threshold
            else:
                if scores:
                    primary_intent = max(scores.items(), key=lambda x: x[1])[0]
                    confidence = scores[primary_intent]
            
            return {
                "primary_intent": primary_intent,
                "scores": scores,
                "confidence": confidence,
                "reason": f"Highest score: {primary_intent} ({confidence:.3f})"
            }
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}", exc_info=True)
            return {
                "primary_intent": "unknown",
                "scores": {},
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }


# Singleton instance
intent_classification_service = IntentClassificationService()

