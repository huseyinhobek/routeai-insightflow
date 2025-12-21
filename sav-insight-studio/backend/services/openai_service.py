"""
OpenAI Service for Twin Transformer
Uses GPT-5 mini with minimal reasoning effort for survey response transformation
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from openai import AsyncOpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)


# JSON Schema for structured output
TRANSFORM_OUTPUT_SCHEMA = {
    "name": "survey_transform_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sentence": {
                            "type": "string",
                            "description": "First-person statement derived from the survey response"
                        },
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Variable names that contributed to this sentence"
                        },
                        "warnings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Any warnings or notes about the transformation"
                        }
                    },
                    "required": ["sentence", "sources", "warnings"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["sentences"],
        "additionalProperties": False
    }
}


SYSTEM_PROMPT = """You are a "survey response to first-person statement transformer".

TASK:
Transform survey responses into first-person statements. These sentences will be used to create a digital twin profile - meaning another AI will read these sentences to understand the person's profile.

RULES:
1. Only use information from the provided variables list
2. Never invent new questions/columns
3. Each sentence must contain at least 1 source, and sources must only consist of input variable names
4. Empty answers are already filtered out, ignore them
5. "No inference": do not make cause-effect, psychological interpretations, or generalizations
6. Do not create double negative sentences (e.g., "I don't not agree")
7. Short, clear but NATURAL sentences: 1 variable → usually 1 sentence
   - Do not create single-word or very short sentences (e.g., "I am male." instead of "My gender is male.")
8. Multiple multi-choice answers can be combined in one sentence but sources must include all
9. If "Other (specify)" open text exists: convey the user's written text in first person
10. For scales, use labels if available; otherwise use "I gave X out of Y" format

INDEPENDENT SENTENCE RULE (CRITICAL):
- Each sentence must be INDEPENDENTLY understandable
- VAGUE EXPRESSIONS like "As mentioned in the question list...", "As stated above...", "The mentioned options..." are FORBIDDEN
- The sentence must be clear enough that someone who hasn't seen the survey can understand it
- Extract the topic from the question/label and include it in the sentence

WRONG EXAMPLES (DON'T DO THESE):
❌ "The financial activities mentioned in the question list apply to me."
❌ "I prefer the mentioned options."
❌ "None of the above apply to me."
❌ "None of the life events listed above..."
❌ "The activities in the list..."
❌ "From the mentioned options..."

For "None of the above" or "none" answers:
- Skip the answer OR
- If it must be included: create a summary sentence like "I had no significant life changes in the last 12 months."

CORRECT EXAMPLES:
✓ "I use online banking and mobile payments." (for financial activities)
✓ "I drink coffee and tea." (for beverage preferences)
✓ "I exercise 3-4 times per week." (for exercise frequency)

ADDITIONAL RULES:
- Do not write variable codes (Q1, D2, S3_R_5, etc.) in the sentence
- For Yes/No questions, state the question content in first person
- Create concrete sentences using the selected answer's label/value

SENTENCE EXAMPLES:
- Demographics: "I am 35 years old.", "I live in Ankara.", "I work in the software sector."
- Yes/No: "I would recommend the product to my friends." or "I would not choose this brand again."
- Scale: "I am very satisfied with customer service." (for satisfaction 5/5)
- Multi-choice: "I shop online, pay bills, and transfer money over the internet."
- Open text: "My suggestion about the company: I want faster delivery."

LANGUAGE:
Always generate sentences in English, regardless of the input language. Translate any non-English content to English while maintaining the meaning and context."""


@dataclass
class VariableInput:
    """Single variable input for transformation"""
    name: str
    question: str
    var_type: str  # single, multi, scale, open, numeric
    answer: Dict[str, Any]  # {raw: any, label: str, labels: [str]}


@dataclass
class ChunkInput:
    """Input payload for a single chunk transformation"""
    job_id: str
    dataset_id: str
    respondent: Dict[str, Any]  # {rowIndex: int, respondentId: str}
    chunk: Dict[str, int]  # {chunkIndex: int, chunkCount: int}
    variables: List[Dict[str, Any]]


@dataclass
class TransformSentence:
    """Single transformed sentence"""
    sentence: str
    sources: List[str]
    warnings: List[str]


@dataclass
class ChunkOutput:
    """Output from a single chunk transformation"""
    sentences: List[TransformSentence]
    success: bool
    error: Optional[str] = None
    retry_count: int = 0
    request_id: Optional[str] = None


class OpenAIService:
    """Service for calling OpenAI API for survey transformation"""
    
    def __init__(self):
        self.client = None
        self.model = settings.OPENAI_MODEL
        self.reasoning_effort = settings.OPENAI_REASONING_EFFORT
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
    def _ensure_client(self):
        """Initialize client if not already done"""
        if self.client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured")
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _build_user_message(self, chunk_input: ChunkInput) -> str:
        """Build the user message with variable data"""
        variables_text = []
        
        for var in chunk_input.variables:
            # Include all options for context if available
            all_options = var.get('all_options', [])
            options_text = ""
            if all_options:
                options_text = f"\nPossible Options: {', '.join(all_options[:10])}"  # Limit to 10 for brevity
                if len(all_options) > 10:
                    options_text += f" (ve {len(all_options) - 10} seçenek daha)"
            
            var_desc = f"""
Variable: {var['name']}
Question/Label: {var['question']}
Type: {var['var_type']}{options_text}
Selected Answer: {json.dumps(var['answer'], ensure_ascii=False)}
"""
            variables_text.append(var_desc)
        
        return f"""Respondent Row: {chunk_input.respondent.get('rowIndex', 'N/A')}
Chunk: {chunk_input.chunk.get('chunkIndex', 0) + 1} / {chunk_input.chunk.get('chunkCount', 1)}

Variables to Transform:
{'---'.join(variables_text)}

Transform each variable's answer into a first-person sentence.
IMPORTANT: Sentences must be independently understandable - DO NOT use vague expressions like "as mentioned in the question list".
Clearly state the question's topic in the sentence (e.g., "I do X activities related to money/finance").
Return a JSON format sentences array.
ALL SENTENCES MUST BE IN ENGLISH."""
    
    def _validate_response(self, response_data: Dict, input_variables: List[str]) -> tuple[bool, List[str]]:
        """Validate the response schema and sources"""
        errors = []
        
        if "sentences" not in response_data:
            errors.append("Missing 'sentences' field")
            return False, errors
        
        if not isinstance(response_data["sentences"], list):
            errors.append("'sentences' must be an array")
            return False, errors
        
        for i, sentence in enumerate(response_data["sentences"]):
            if "sentence" not in sentence:
                errors.append(f"Sentence {i}: missing 'sentence' field")
            if "sources" not in sentence:
                errors.append(f"Sentence {i}: missing 'sources' field")
            elif isinstance(sentence.get("sources"), list):
                # Validate sources are from input variables
                for source in sentence["sources"]:
                    if source not in input_variables:
                        errors.append(f"Sentence {i}: invalid source '{source}' not in input variables")
        
        return len(errors) == 0, errors
    
    async def transform_chunk(self, chunk_input: ChunkInput) -> ChunkOutput:
        """Transform a chunk of variables for a single respondent"""
        self._ensure_client()
        
        input_var_names = [v["name"] for v in chunk_input.variables]
        user_message = self._build_user_message(chunk_input)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                print(f"[OPENAI] Calling model={self.model} for row {chunk_input.respondent.get('rowIndex')}, vars={len(chunk_input.variables)}")
                
                # Build API call params for GPT-5 mini (supports reasoning_effort)
                api_params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": TRANSFORM_OUTPUT_SCHEMA
                    },
                    "max_completion_tokens": 4096,
                    "reasoning_effort": self.reasoning_effort  # GPT-5 mini supports this
                }
                
                try:
                    response = await self.client.chat.completions.create(**api_params)
                    print(f"[OPENAI] Got response for row {chunk_input.respondent.get('rowIndex')}")
                except Exception as api_err:
                    print(f"[OPENAI] API call failed: {api_err}")
                    raise
                
                # Parse response
                content = response.choices[0].message.content
                response_data = json.loads(content)
                
                # Validate response
                is_valid, validation_errors = self._validate_response(response_data, input_var_names)
                
                if not is_valid:
                    last_error = f"Validation failed: {'; '.join(validation_errors)}"
                    print(f"[OPENAI] Validation FAILED (attempt {attempt + 1}): {last_error}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        return ChunkOutput(
                            sentences=[],
                            success=False,
                            error=last_error,
                            retry_count=attempt + 1,
                            request_id=response.id if hasattr(response, 'id') else None
                        )
                
                # Parse sentences
                sentences = []
                for s in response_data["sentences"]:
                    sentences.append(TransformSentence(
                        sentence=s["sentence"],
                        sources=s.get("sources", []),
                        warnings=s.get("warnings", [])
                    ))
                
                return ChunkOutput(
                    sentences=sentences,
                    success=True,
                    retry_count=attempt,
                    request_id=response.id if hasattr(response, 'id') else None
                )
                
            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {str(e)}"
                logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                
            except Exception as e:
                last_error = f"API error: {str(e)}"
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {e}")
                
                # Check for rate limit
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    await asyncio.sleep(self.retry_delay * (attempt + 1) * 2)
                elif "5" in str(getattr(e, 'status_code', '')):  # 5xx errors
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return ChunkOutput(
            sentences=[],
            success=False,
            error=last_error,
            retry_count=self.max_retries
        )
    
    async def transform_row(
        self,
        job_id: str,
        dataset_id: str,
        row_index: int,
        respondent_id: Optional[str],
        variables: List[Dict[str, Any]],
        chunk_size: int = 30
    ) -> Dict[str, Any]:
        """Transform all variables for a single row, splitting into chunks if needed"""
        
        # Split variables into chunks
        chunks = []
        for i in range(0, len(variables), chunk_size):
            chunks.append(variables[i:i + chunk_size])
        
        print(f"[OPENAI] transform_row: row={row_index}, total_vars={len(variables)}, chunks={len(chunks)} (parallel)")
        
        # Create all chunk inputs
        chunk_inputs = []
        for chunk_index, chunk_vars in enumerate(chunks):
            chunk_input = ChunkInput(
                job_id=job_id,
                dataset_id=dataset_id,
                respondent={"rowIndex": row_index, "respondentId": respondent_id},
                chunk={"chunkIndex": chunk_index, "chunkCount": len(chunks)},
                variables=chunk_vars
            )
            chunk_inputs.append((chunk_index, chunk_vars, chunk_input))
        
        # Process all chunks in PARALLEL
        async def process_chunk(chunk_index: int, chunk_vars: List, chunk_input: ChunkInput):
            result = await self.transform_chunk(chunk_input)
            return chunk_index, chunk_vars, result
        
        tasks = [process_chunk(idx, vars, inp) for idx, vars, inp in chunk_inputs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"[OPENAI] Row {row_index}: all {len(chunks)} chunks done (parallel)")
        
        # Collect results in order
        all_sentences = []
        all_traces = []
        total_retries = 0
        
        # Sort by chunk_index to maintain order
        for item in sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else 999):
            if isinstance(item, Exception):
                logger.error(f"Chunk exception for row {row_index}: {item}")
                all_traces.append({
                    "chunkIndex": -1,
                    "sentVars": [],
                    "modelRequestId": None,
                    "parsedOk": False,
                    "errors": [str(item)],
                    "retryCount": 0
                })
                continue
            
            chunk_index, chunk_vars, result = item
            
            # Collect trace info
            trace = {
                "chunkIndex": chunk_index,
                "sentVars": [v["name"] for v in chunk_vars],
                "modelRequestId": result.request_id,
                "parsedOk": result.success,
                "errors": [result.error] if result.error else [],
                "retryCount": result.retry_count
            }
            all_traces.append(trace)
            total_retries += result.retry_count
            
            if result.success:
                for sentence in result.sentences:
                    all_sentences.append(asdict(sentence))
            else:
                # Log error but continue with other chunks
                logger.error(f"Chunk {chunk_index} failed for row {row_index}: {result.error}")
        
        return {
            "sentences": all_sentences,
            "rawTrace": {"perChunk": all_traces},
            "totalRetries": total_retries,
            "success": any(t["parsedOk"] for t in all_traces)
        }


# Singleton instance
openai_service = OpenAIService()

