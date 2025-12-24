"""
Smart Filter suggestion service

Goal:
- Send ONLY metadata (variable code + question text/label + type + cardinality + response rate + sample value labels)
- Ask the model to propose useful dashboard filters (segmentation)
- Return structured output (SmartFilterResponse-like)
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI  # type: ignore[import-not-found]

from config import settings


SMART_FILTER_OUTPUT_SCHEMA: Dict[str, Any] = {
    "name": "smart_filter_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "filters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "sourceVars": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "filterType": {
                            "type": "string",
                            "enum": ["categorical", "ordinal", "numeric_range", "multi_select", "date_range"],
                        },
                        "ui": {
                            "type": "object",
                            "properties": {
                                "control": {
                                    "type": "string",
                                    "enum": ["checkbox_group", "select", "range_slider", "date_picker"],
                                }
                            },
                            "required": ["control"],
                            "additionalProperties": False,
                        },
                        "suitabilityScore": {"type": "integer"},
                        "rationale": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "title",
                        "description",
                        "sourceVars",
                        "filterType",
                        "ui",
                        "suitabilityScore",
                        "rationale",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["filters"],
        "additionalProperties": False,
    },
}


SYSTEM_PROMPT = """ROLE:
You are an expert survey data analyst.

TASK:
I will provide you with a survey variable dictionary (metadata only): variable code, question text (label), data type, cardinality, response rate, and example value labels.
Based solely on this metadata, propose the most useful “Smart Filters” for a dashboard.

CRITICAL CONSTRAINTS (MUST FOLLOW):
- You DO NOT have respondent-level data. You only have metadata. Do NOT guess distributions or outcomes. No hallucinations.
- Use ONLY the provided variable codes in sourceVars.
- Each Smart Filter MUST be based on EXACTLY ONE variable code.
  - Therefore, sourceVars MUST always be a single-element array, e.g., ["D2"].
  - Multi-select / multi-response / grid-combining is NOT allowed.
- Do NOT propose admin/technical/paradata fields as filters (avoid entirely), such as:
  respondent id, record id, uuid, weight, timestamp, start/end time, duration/LOI, quota, base flags,
  internal QA flags, device/ip/user-agent, geolocation precision fields, system fields, import/export keys.
- Prefer variables with:
  - high responseRate
  - low/medium cardinality (ideally 2–20)
- Goal: enable meaningful segmentation for digital profiling (demographics, ownership/usage, behavior, attitudes where appropriate).

SELECTION PRIORITIES:
1) Core demographics/profile splits (age group, gender, region, income band, education, life stage)
2) Ownership / membership / subscription / usage status variables (e.g., “has X”, “uses X”, “is a customer”)
3) Purchase behavior / channel / spend band / frequency (if cardinality remains manageable)
4) Attitudinal or satisfaction/NPS-style measures ONLY if they support segmentation and cardinality is not excessive

EXCLUSIONS / AVOID:
- Very high cardinality variables (e.g., > 30) unless it is clearly a standard segmentation field and still manageable
- Free-text / open-ended / “Other (specify)” variables
- Very low responseRate (e.g., < 0.40) unless there is a strong segmentation rationale

OUTPUT REQUIREMENTS:
- Output MUST be valid JSON only.
- Return an object with a single key: "filters" (an array).
- All text MUST be in English: title, description, rationale.
- Each filter object MUST follow this shape:

{
  "id": "stable_snake_case_id",
  "title": "Short UI Title",
  "description": "One-sentence user-friendly description.",
  "sourceVars": ["VARIABLE_CODE"],
  "filterType": "categorical" | "ordinal" | "numeric_range" | "date_range",
  "ui": { "control": "select" | "checkbox_group" | "range_slider" | "date_range" },
  "suitabilityScore": 0-100,
  "rationale": "1–2 sentences explaining why this variable is valuable for segmentation, referencing metadata signals (responseRate/cardinality/type/value labels) without inventing data."
}

SCORING GUIDELINES (FOR suitabilityScore):
Produce a 0–100 suitabilityScore using these heuristics (do not show the calculation):
- Start from a base of 50.
- Add up to +30 based on responseRate (higher = better).
- Add up to +20 based on cardinality fit (2–20 best; penalize > 20).
- Subtract heavily (or exclude entirely) if the variable appears admin/technical/open-ended/high-cardinality.
- Boost (+5 to +15) if the label/value labels clearly indicate strong segmentation utility (e.g., demographics, ownership/usage, subscription status).

IMPORTANT:
- Do not include any variables not present in the provided metadata.
- Do not output any extra keys outside the specified JSON structure.
- Do not add commentary outside the JSON.

"""


class SmartFilterService:
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = getattr(settings, "SMART_FILTER_MODEL", None) or settings.OPENAI_MODEL
        self.reasoning_effort = getattr(settings, "SMART_FILTER_REASONING_EFFORT", None) or "minimal"
        self.max_retries = 2

    def _ensure_client(self):
        if self.client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured")
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_user_message(self, variables: List[Dict[str, Any]], max_filters: int) -> str:
        # Keep payload manageable: prefer candidates that are useful for filtering
        # (categorical-ish, high response, moderate cardinality)
        def score(v: Dict[str, Any]) -> float:
            rr = float(v.get("responseRate") or 0)
            card = float(v.get("cardinality") or 0)
            # prefer rr high, card moderate (penalize very high)
            penalty = 0.0
            if card > 50:
                penalty += 50.0
            elif card > 20:
                penalty += 10.0
            return rr - penalty

        vars_sorted = sorted(variables, key=score, reverse=True)
        vars_trimmed = vars_sorted[:160]

        payload = []
        for v in vars_trimmed:
            payload.append({
                "code": v.get("code"),
                "questionText": v.get("label") or v.get("code"),
                "type": v.get("type"),
                "measure": v.get("measure"),
                "cardinality": v.get("cardinality"),
                "responseRate": v.get("responseRate"),
                "valueLabelsSample": [
                    (vl.get("label") if isinstance(vl, dict) else str(vl))
                    for vl in (v.get("valueLabels") or [])[:8]
                ],
            })

        return f"""Below is a variable dictionary. The "code" field is the EXACT column name in the dataset - you MUST use these exact codes in sourceVars.

CRITICAL: The "code" values are the ACTUAL database column names. Do NOT modify, rename, or invent new codes. 
Use ONLY the exact "code" values provided (e.g., "D1", "D1_R1", "AGE_GENDER_USA").

Propose up to {max_filters} Smart Filters.

Variables (JSON):
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""

    async def suggest_filters(
        self,
        variables: List[Dict[str, Any]],
        max_filters: int = 8,
    ) -> Dict[str, Any]:
        self._ensure_client()
        user_message = self._build_user_message(variables, max_filters=max_filters)

        last_error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                # NOTE: Some GPT-5 models (e.g., gpt-5-mini) do not support custom temperature values.
                # To stay compatible, we omit temperature and rely on the model default.
                api_params: Dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "response_format": {"type": "json_schema", "json_schema": SMART_FILTER_OUTPUT_SCHEMA},
                    "max_completion_tokens": 2048,
                    "reasoning_effort": self.reasoning_effort,
                }

                # For non-GPT-5 models, you may optionally enable temperature again.
                if not str(self.model).startswith("gpt-5"):
                    api_params["temperature"] = 0.2

                resp = await self.client.chat.completions.create(**api_params)
                content = resp.choices[0].message.content
                data = json.loads(content or "{}")
                if not isinstance(data, dict) or "filters" not in data:
                    raise ValueError("Invalid response: missing filters")
                return data
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(0.75 * (attempt + 1))
                    continue
                raise


smart_filter_service = SmartFilterService()


