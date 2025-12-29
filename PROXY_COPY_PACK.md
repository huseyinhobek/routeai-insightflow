# Proxy Copy Pack - Tier0-3 (TR + EN)

## Tier0: Direct Measure

### EN
- **Banner Title**: "Direct preference measure available"
- **Limitation Statement**: "This measures stated preference directly from the dataset."
- **What We Can Measure**: "Preference distribution and segment differences"
- **What We Cannot Claim**:
  - "Actual purchase behavior (stated ≠ revealed preference)"
  - "Long-term loyalty or switching intent"
- **Follow-up Templates**:
  - "What drives preference for {var_code}?"
  - "Compare {var_code} preference between {audience} and total sample"
  - "Which segments over-index for the top choice in {var_code}?"
  - "What is the correlation between {var_code} and satisfaction scores?"

### TR
- **Banner Title**: "Doğrudan tercih ölçümü mevcut"
- **Limitation Statement**: "Bu, veri setinden doğrudan belirtilen tercihi ölçer."
- **What We Can Measure**: "Tercih dağılımı ve segment farkları"
- **What We Cannot Claim**:
  - "Gerçek satın alma davranışı (belirtilen ≠ gerçek tercih)"
  - "Uzun vadeli sadakat veya değiştirme niyeti"
- **Follow-up Templates**:
  - "{var_code} için tercihi ne belirliyor?"
  - "{var_code} tercihini {audience} ve toplam örnek arasında karşılaştır"
  - "Hangi segmentler {var_code}'da en çok seçilen seçenek için fazla endeksleniyor?"
  - "{var_code} ile memnuniyet skorları arasındaki korelasyon nedir?"

---

## Tier1: Close Proxy (Intent/Consideration/Satisfaction)

### EN
- **Banner Title**: "Using intent/consideration as preference proxy"
- **Limitation Statement**: "This measures purchase intent or consideration, which correlates with but is not identical to preference."
- **What We Can Measure**: "Intent distribution, consideration set, satisfaction scores"
- **What We Cannot Claim**:
  - "Direct preference ranking (intent ≠ preference)"
  - "Purchase probability without additional context"
- **Follow-up Templates**:
  - "What is the distribution of preference for {var_code}?"
  - "Compare consideration set between {audience} and total"
  - "Which factors drive intent for {brand_a} vs {brand_b}?"
  - "What is the correlation between intent and actual purchase behavior?"

### TR
- **Banner Title**: "Niyet/değerlendirme tercih proxy'si olarak kullanılıyor"
- **Limitation Statement**: "Bu, satın alma niyetini veya değerlendirmeyi ölçer; tercihle korelasyon gösterir ancak özdeş değildir."
- **What We Can Measure**: "Niyet dağılımı, değerlendirme seti, memnuniyet skorları"
- **What We Cannot Claim**:
  - "Doğrudan tercih sıralaması (niyet ≠ tercih)"
  - "Ek bağlam olmadan satın alma olasılığı"
- **Follow-up Templates**:
  - "{var_code} için tercih dağılımı nedir?"
  - "Değerlendirme setini {audience} ve toplam arasında karşılaştır"
  - "{brand_a} vs {brand_b} için niyeti ne belirliyor?"
  - "Niyet ile gerçek satın alma davranışı arasındaki korelasyon nedir?"

---

## Tier2: Indirect Proxy (Drivers/Attributes)

### EN
- **Banner Title**: "Using attribute perceptions as preference proxy"
- **Limitation Statement**: "This measures attribute perceptions (trust, value, quality) that may influence preference but do not directly measure it."
- **What We Can Measure**: "Attribute scores, driver importance, perceived quality"
- **What We Cannot Claim**:
  - "Direct preference or choice (attributes ≠ preference)"
  - "Which option respondents would actually choose"
- **Follow-up Templates**:
  - "What is the distribution of preference/choice for {var_code}?"
  - "Compare attribute perceptions between {audience} and total"
  - "Which attributes drive preference for {brand_a}?"
  - "What is the correlation between {var_code} and purchase intent?"

### TR
- **Banner Title**: "Özellik algıları tercih proxy'si olarak kullanılıyor"
- **Limitation Statement**: "Bu, tercihi etkileyebilecek özellik algılarını (güven, değer, kalite) ölçer ancak tercihi doğrudan ölçmez."
- **What We Can Measure**: "Özellik skorları, belirleyici önem, algılanan kalite"
- **What We Cannot Claim**:
  - "Doğrudan tercih veya seçim (özellikler ≠ tercih)"
  - "Katılımcıların gerçekte hangi seçeneği seçeceği"
- **Follow-up Templates**:
  - "{var_code} için tercih/seçim dağılımı nedir?"
  - "Özellik algılarını {audience} ve toplam arasında karşılaştır"
  - "Hangi özellikler {brand_a} için tercihi belirliyor?"
  - "{var_code} ile satın alma niyeti arasındaki korelasyon nedir?"

---

## Tier3: Weak Proxy (Awareness/Knowledge)

### EN
- **Banner Title**: "Using awareness/knowledge as preference proxy"
- **Limitation Statement**: "⚠️ WARNING: This measures familiarity/knowledge, NOT preference. Familiarity does not equal preference."
- **What We Can Measure**: "Awareness levels, knowledge distribution, familiarity scores"
- **What We Cannot Claim**:
  - "Preference or choice (awareness ≠ preference)"
  - "Purchase intent or consideration"
  - "Which option respondents prefer or would choose"
- **Follow-up Templates**:
  - "What is the distribution of preference/choice for {var_code}?"
  - "Compare preference between {audience} and total sample"
  - "What drives preference for {brand_a} vs {brand_b}?"
  - "What is the consideration set for {var_code}?"
  - "Which segments prefer {var_code}?"

### TR
- **Banner Title**: "Farkındalık/bilgi tercih proxy'si olarak kullanılıyor"
- **Limitation Statement**: "⚠️ UYARI: Bu, tanıdıklık/bilgiyi ölçer, tercihi DEĞİL. Tanıdıklık tercih anlamına gelmez."
- **What We Can Measure**: "Farkındalık seviyeleri, bilgi dağılımı, tanıdıklık skorları"
- **What We Cannot Claim**:
  - "Tercih veya seçim (farkındalık ≠ tercih)"
  - "Satın alma niyeti veya değerlendirme"
  - "Katılımcıların tercih ettiği veya seçeceği seçenek"
- **Follow-up Templates**:
  - "{var_code} için tercih/seçim dağılımı nedir?"
  - "Tercihi {audience} ve toplam örnek arasında karşılaştır"
  - "{brand_a} vs {brand_b} için tercihi ne belirliyor?"
  - "{var_code} için değerlendirme seti nedir?"
  - "Hangi segmentler {var_code}'u tercih ediyor?"

---

## Policy Mapping + Thresholds

### Severity Levels

**Input**: `(tier, confidence, base_n, top2_gap_pp)`

**Output**: `severity` + `auto_risk_averse`

| Tier | Confidence | Base N | Top2 Gap | Severity | Auto Risk-Averse |
|------|------------|--------|----------|----------|------------------|
| 0    | >= 0.85    | >= 100 | >= 5pp   | info     | false            |
| 0    | < 0.85     | < 100  | < 5pp    | warn     | true             |
| 1    | >= 0.70    | >= 100 | >= 5pp   | info     | false            |
| 1    | < 0.70     | < 100  | < 5pp    | warn     | true             |
| 2    | >= 0.55    | >= 100 | >= 5pp   | warn     | false            |
| 2    | < 0.55     | < 100  | < 5pp    | risk     | true             |
| 3    | any        | any    | any      | risk     | true (if base_n<100 or gap<5pp) |

**Low Confidence Flag**: `base_n < 100 OR top2_gap_pp < 5 OR confidence < tier_threshold`

**Tier Thresholds**:
- Tier0: 0.85
- Tier1: 0.70
- Tier2: 0.55
- Tier3: 0.45 (always low confidence)

---

## Implementation: Types + Pseudo-code + Sample JSON

### TypeScript Types

```typescript
type ProxyTier = 0 | 1 | 2 | 3;
type SeverityLevel = 'info' | 'warn' | 'risk';
type Locale = 'en' | 'tr';

interface ProxyCopy {
  tier: ProxyTier;
  tier_name: string;
  banner_title: string;
  limitation_statement: string;
  what_we_can_measure: string;
  what_we_cannot_claim: string[];
  follow_up_templates: string[];
  severity: SeverityLevel;
  low_confidence_flag: boolean;
  auto_risk_averse: boolean;
}

interface ProxyBannerProps {
  copy: ProxyCopy;
  proxy_var_code: string;
  confidence: number;
  alternatives?: Array<{
    var_code: string;
    tier: ProxyTier;
    confidence: number;
  }>;
}
```

### Backend Pseudo-code

```python
def get_proxy_copy(
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
    
    # Load copy pack from dict (Tier0-3, EN/TR)
    copy_pack = COPY_PACKS[locale][tier]
    
    # Append low confidence suffix if flag is True
    if low_confidence_flag:
        copy_pack['limitation_statement'] += (
            " (Low confidence due to small sample or close results)"
            if locale == 'en' else
            " (Küçük örnek veya yakın sonuçlar nedeniyle düşük güven)"
        )
    
    return {
        **copy_pack,
        'tier': tier,
        'severity': severity,
        'low_confidence_flag': low_confidence_flag,
        'auto_risk_averse': auto_risk_averse
    }
```

### Sample JSON Response (Tier3)

```json
{
  "tier": 3,
  "tier_name": "Knowledge/Awareness",
  "banner_title": "Using awareness/knowledge as preference proxy",
  "limitation_statement": "⚠️ WARNING: This measures familiarity/knowledge, NOT preference. Familiarity does not equal preference. (Low confidence due to small sample or close results)",
  "what_we_can_measure": "Awareness levels, knowledge distribution, familiarity scores",
  "what_we_cannot_claim": [
    "Preference or choice (awareness ≠ preference)",
    "Purchase intent or consideration",
    "Which option respondents prefer or would choose"
  ],
  "follow_up_templates": [
    "What is the distribution of preference/choice for {var_code}?",
    "Compare preference between {audience} and total sample",
    "What drives preference for {brand_a} vs {brand_b}?",
    "What is the consideration set for {var_code}?",
    "Which segments prefer {var_code}?"
  ],
  "severity": "risk",
  "low_confidence_flag": true,
  "auto_risk_averse": true,
  "proxy_var_code": "QV1_3",
  "confidence": 0.45
}
```

---

## Frontend Component Structure

```typescript
<ProxyBanner
  copy={proxyCopy}
  proxy_var_code="QV1_3"
  confidence={0.45}
  alternatives={[...]}
/>

// Renders:
// - Banner with tier badge + title
// - Limitation statement (always visible)
// - Expandable "What we cannot claim" section
// - "Next best questions" chips (from follow_up_templates)
```

