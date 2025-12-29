"""
RAG service for semantic retrieval over utterances
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
import asyncio

from models import Utterance, Variable
from services.embedding_service import embedding_service
from database import DATABASE_AVAILABLE
from config import settings

logger = logging.getLogger(__name__)

# JSON Schema for RAG synthesis output
RAG_SYNTHESIS_OUTPUT_SCHEMA = {
    "name": "rag_synthesis_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "themes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "support_count": {"type": "integer"},
                        "representative_quotes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "respondent_id": {"type": "integer"},
                                    "var_code": {"type": "string"}
                                },
                                "required": ["text", "respondent_id", "var_code"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["description", "support_count", "representative_quotes"],
                    "additionalProperties": False
                }
            },
            "narrative": {"type": "string"}
        },
        "required": ["themes", "narrative"],
        "additionalProperties": False
    }
}

RAG_SYNTHESIS_SYSTEM_PROMPT = """Sen bir anket veri analizcisisin. Görevin, alınan anket cevaplarından temaları sentezlemek.

KRİTİK KURALLAR:
1. SADECE verilen alıntılardan/aktarımlardan bilgi kullanmalısın. Gösterilenlerin ötesinde uydurma veya genelleme yapma.
2. Genel yüzdeler veya istatistikler belirtme (örn., "Katılımcıların %X'i"). Sadece alınan örneği referans al.
3. Sonuçları her zaman "alınan örnekte" veya "bu cevaplar arasında" şeklinde ifade et.
4. Her tema, alıntılardan en az 1-3 temsilci alıntı ile desteklenmeli.
5. Benzer cevapları tutarlı temalarda grupla.
6. Nüfus düzeyinde iddialarda bulunmadan temaları sentezleyen bir özet anlatı sağla.

ÇIKTI:
- themes: Her biri bir açıklama, support_count (alıntı sayısı) ve temsilci alıntılar içeren tema nesneleri dizisi
- narrative: Temaları birbirine bağlayan, alınan örnek açısından ifade edilen 2-3 cümlelik özet (TÜRKÇE)"""


class RAGService:
    """Service for RAG retrieval and synthesis"""
    
    def __init__(self):
        pass
    
    def retrieve_utterances(
        self,
        db: Session,
        dataset_id: str,
        question_text: str,
        audience_id: Optional[str] = None,
        variable_id: Optional[int] = None,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-K utterances by semantic similarity
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            question_text: User question
            audience_id: Optional audience ID to filter by membership
            variable_id: Optional variable ID for variable-specific RAG (open-text)
            top_k: Number of utterances to retrieve
            
        Returns:
            List of utterance dicts with provenance
        """
        if not DATABASE_AVAILABLE:
            return []
        
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(question_text)
        if not query_embedding:
            logger.warning("Failed to generate query embedding for RAG retrieval")
            return []
        
        # Retrieve utterances using embedding service
        utterances = embedding_service.get_utterance_embeddings(
            db=db,
            dataset_id=dataset_id,
            query_vector=query_embedding,
            top_k=top_k,
            audience_id=audience_id,
            variable_id=variable_id
        )
        
        return utterances
    
    def build_evidence_json(
        self,
        utterances: List[Dict[str, Any]],
        question_text: str
    ) -> Dict[str, Any]:
        """
        Build evidence_json from retrieved utterances
        
        Returns:
            evidence_json with retrieved_count, citations
        """
        citations = []
        
        for utt in utterances:
            citation = {
                "respondent_id": utt.get('respondent_id'),
                "variable_id": utt.get('variable_id'),
                "var_code": utt.get('var_code'),
                "snippet": utt.get('display_text', ''),
                "question_text": utt.get('provenance', {}).get('question_text', '') if isinstance(utt.get('provenance'), dict) else '',
                "score": utt.get('score', 0.0)
            }
            citations.append(citation)
        
        evidence_json = {
            "retrieved_count": len(utterances),
            "citations": citations,
            "question_text": question_text
        }
        
        # If no utterances retrieved, explicitly signal "not ready" state
        if len(utterances) == 0:
            evidence_json["not_ready"] = True
            evidence_json["not_ready_message"] = "Embeddings not ready / utterances not generated"
        
        return evidence_json
    
    async def synthesize_with_llm(
        self,
        evidence_json: Dict[str, Any],
        question_text: str
    ) -> Dict[str, Any]:
        """
        Synthesize themes from evidence using LLM
        
        Args:
            evidence_json: Dict with citations from build_evidence_json
            question_text: Original user question
            
        Returns:
            Dict with themes, caveats, narrative
        """
        citations = evidence_json.get('citations', [])
        
        if not citations:
            # Return empty result if no citations
            return {
                "themes": [],
                "caveats": ["Alıntı alınamadı"],
                "narrative": "Alınan örnekte ilgili cevap bulunamadı."
            }
        
        # Build user message with citations
        citations_text = []
        for i, cit in enumerate(citations, 1):
            citations_text.append(
                f"[{i}] Respondent {cit.get('respondent_id', 'N/A')}, Variable {cit.get('var_code', 'N/A')}:\n"
                f"Question: {cit.get('question_text', 'N/A')}\n"
                f"Response: {cit.get('snippet', '')}\n"
            )
        
        user_message = f"""Soru: {question_text}

{len(citations)} ilgili cevap alındı:

{''.join(citations_text)}

Lütfen bu cevapları analiz et ve ana temaları belirle. Unutma:
- Sadece yukarıdaki alıntılardan bilgi kullan
- Genel yüzdeler veya istatistikler belirtme
- Sonuçları "alınan örnekte" veya "bu cevaplar arasında" şeklinde ifade et
- Her tema yukarıdaki alıntılardan en az 1-3 temsilci alıntı içermeli
- TÜM ÇIKTI TÜRKÇE OLMALI"""
        
        # Call OpenAI API (async)
        try:
            from openai import AsyncOpenAI
            
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not configured, returning basic synthesis")
                return self._fallback_synthesis(citations, question_text)
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            model = settings.OPENAI_MODEL
            
            # Build API call params
            api_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": RAG_SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": RAG_SYNTHESIS_OUTPUT_SCHEMA
                },
                "max_completion_tokens": 2048,
            }
            
            # Add reasoning_effort for GPT-5 models
            if model.startswith("gpt-5"):
                api_params["reasoning_effort"] = "minimal"
            
            # Call async API directly (we're in async context)
            response = await client.chat.completions.create(**api_params)
            content = response.choices[0].message.content
            response_data = json.loads(content)
            
            # Validate and extract themes and narrative
            themes = response_data.get("themes", [])
            narrative = response_data.get("narrative", "")
            
            # Add caveats
            caveats = [
                "Sonuçlar alınan örneğe dayanmaktadır, nüfus yüzdelerine değil",
                f"Örnek boyutu: {len(citations)}"
            ]
            
            return {
                "themes": themes,
                "caveats": caveats,
                "narrative": narrative
            }
                
        except Exception as e:
            logger.error(f"Error synthesizing with LLM: {e}", exc_info=True)
            # Fallback to basic synthesis
            return self._fallback_synthesis(citations, question_text)
    
    def _fallback_synthesis(
        self,
        citations: List[Dict[str, Any]],
        question_text: str
    ) -> Dict[str, Any]:
        """
        Fallback synthesis when LLM is not available or fails
        """
        themes = []
        if citations:
            themes.append({
                "description": "Retrieved responses",
                "support_count": len(citations),
                "representative_quotes": [
                    {
                        "text": cit.get('snippet', ''),
                        "respondent_id": cit.get('respondent_id'),
                        "var_code": cit.get('var_code', '')
                    }
                    for cit in citations[:10]  # Top 10 quotes
                ]
            })
        
        narrative = f"Alınan {len(citations)} cevap örneğinde, '{question_text}' hakkında çeşitli bakış açıları bulundu."
        
        return {
            "themes": themes,
            "caveats": [
                "Sonuçlar alınan örneğe dayanmaktadır, nüfus yüzdelerine değil",
                f"Örnek boyutu: {len(citations)}"
            ],
            "narrative": narrative
        }


# Singleton instance
rag_service = RAGService()

