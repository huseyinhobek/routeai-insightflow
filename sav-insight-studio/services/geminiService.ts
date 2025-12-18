import { GoogleGenAI, Type, Schema } from "@google/genai";
import { DatasetMeta, VariableSummary, SmartFilterResponse } from "../types";

// Get API key from Vite environment variables
const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || import.meta.env.GEMINI_API_KEY || '';

// Schema definition for Structured Output
const SmartFilterSchema: Schema = {
  type: Type.OBJECT,
  properties: {
    filters: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          id: { type: Type.STRING },
          title: { type: Type.STRING },
          description: { type: Type.STRING },
          sourceVars: { type: Type.ARRAY, items: { type: Type.STRING } },
          filterType: { 
            type: Type.STRING, 
            enum: ['categorical', 'ordinal', 'numeric_range', 'multi_select', 'date_range'] 
          },
          ui: {
            type: Type.OBJECT,
            properties: {
              control: { 
                type: Type.STRING,
                enum: ['checkbox_group', 'select', 'range_slider', 'date_picker']
              }
            }
          },
          suitabilityScore: { type: Type.INTEGER },
          rationale: { type: Type.STRING },
          // Note: Options are populated by the backend after AI suggests *which* vars to use
          // We ask AI to suggest the logic, not the exact counts (which it doesn't have)
        },
        required: ["id", "title", "sourceVars", "filterType", "ui", "suitabilityScore", "rationale"]
      }
    }
  }
};

class GeminiService {
  private client: GoogleGenAI | null = null;
  private apiKey: string;

  constructor() {
    this.apiKey = GEMINI_API_KEY;
    if (this.apiKey) {
      this.client = new GoogleGenAI({ apiKey: this.apiKey });
    }
  }

  /**
   * Suggests smart filters based on dataset metadata.
   * Note: We do NOT send respondent-level data, only metadata (labels, types).
   */
  async suggestSmartFilters(dataset: DatasetMeta): Promise<SmartFilterResponse> {
    if (!this.apiKey || !this.client) {
      console.warn("Gemini API Key missing. Returning mock data.");
      // Return mock data for demo purposes
      return this.getMockFilters(dataset);
    }

    // Prepare context: Limit to top 100 interesting variables to fit context window if needed
    // Prefer categorical/scale variables with low-ish cardinality
    const interestingVars = dataset.variables
      .filter(v => v.cardinality > 1 && v.cardinality < 50) 
      .slice(0, 80)
      .map(v => ({
        code: v.code,
        label: v.label,
        type: v.type,
        cardinality: v.cardinality,
        valueLabels: v.valueLabels.slice(0, 5).map(vl => vl.label).join(", ") // Sample values
      }));

    const prompt = `
      You are an expert data analyst. Analyze the following variable dictionary from a survey dataset (.sav).
      Suggest 6-8 "Smart Filters" that would be most useful for a dashboard user to slice and dice this data.
      
      Focus on demographics (Age, Gender, Region, Income) and key segmentation variables (Product Usage, Satisfaction tiers).
      
      Variables:
      ${JSON.stringify(interestingVars, null, 2)}
      
      Return a JSON object conforming to the schema. 
      For 'sourceVars', use the exact 'code' from the list.
    `;

    try {
      const response = await this.client.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: prompt,
        config: {
          responseMimeType: "application/json",
          responseSchema: SmartFilterSchema,
          systemInstruction: "You are a helpful data assistant.",
          temperature: 0.2, // Low temp for consistent structural output
        }
      });

      const text = response.text;
      if (!text) throw new Error("No response from Gemini");
      
      const result = JSON.parse(text) as SmartFilterResponse;
      
      // Post-processing: Filter out hallucinations (vars that don't exist)
      const validVarCodes = new Set(dataset.variables.map(v => v.code));
      result.filters = result.filters.filter(f => 
        f.sourceVars.every(sv => validVarCodes.has(sv))
      );

      return result;

    } catch (error) {
      console.error("Gemini Smart Filter Error:", error);
      // Return mock data on error
      return this.getMockFilters(dataset);
    }
  }

  /**
   * Returns intelligent filter suggestions based on deep dataset analysis
   * Analyzes variable patterns, naming conventions, and data characteristics
   */
  private getMockFilters(dataset: DatasetMeta): SmartFilterResponse {
    const filters: SmartFilterResponse['filters'] = [];
    const variables = dataset.variables || [];
    const usedVarCodes = new Set<string>();

    // Helper function to check if variable matches patterns
    const matchesPatterns = (v: VariableSummary, patterns: string[]): boolean => {
      const code = v.code.toLowerCase();
      const label = v.label.toLowerCase();
      return patterns.some(p => code.includes(p) || label.includes(p));
    };

    // Helper to add filter and track used variables
    const addFilter = (filter: SmartFilterResponse['filters'][0]) => {
      filters.push(filter);
      filter.sourceVars.forEach(v => usedVarCodes.add(v));
    };

    // ============================================
    // 1. DEMOGRAPHIC FILTERS (Priority: Highest)
    // ============================================

    // Age filters
    const agePatterns = ['age', 'birth', 'age_group', 'agegroup', 'born'];
    const ageVars = variables.filter(v => matchesPatterns(v, agePatterns) && !usedVarCodes.has(v.code));
    if (ageVars.length > 0) {
      const ageVar = ageVars[0];
      addFilter({
        id: 'filter_age',
        title: 'Age Group',
        description: 'Segment respondents by age demographics for generational insights',
        sourceVars: [ageVar.code],
        filterType: 'categorical',
        ui: { control: ageVar.cardinality > 6 ? 'select' : 'checkbox_group' },
        options: [],
        suitabilityScore: 10,
        rationale: `Age is a fundamental demographic variable. "${ageVar.label}" has ${ageVar.cardinality} categories with ${ageVar.responseRate?.toFixed(0) || 0}% response rate, ideal for generational analysis.`
      });
    }

    // Gender filters
    const genderPatterns = ['gender', 'sex', 'male', 'female'];
    const genderVars = variables.filter(v => matchesPatterns(v, genderPatterns) && !usedVarCodes.has(v.code) && v.cardinality <= 5);
    if (genderVars.length > 0) {
      const genderVar = genderVars[0];
      addFilter({
        id: 'filter_gender',
        title: 'Gender',
        description: 'Filter by respondent gender for demographic segmentation',
        sourceVars: [genderVar.code],
        filterType: 'categorical',
        ui: { control: 'checkbox_group' },
        options: [],
        suitabilityScore: 9,
        rationale: `Gender segmentation enables comparative analysis across demographic groups. High response rate ensures reliable filtering.`
      });
    }

    // Region/Location filters
    const regionPatterns = ['region', 'country', 'city', 'location', 'state', 'province', 'geo', 'area', 'territory', 'district'];
    const regionVars = variables.filter(v => matchesPatterns(v, regionPatterns) && !usedVarCodes.has(v.code));
    if (regionVars.length > 0) {
      const regionVar = regionVars[0];
      addFilter({
        id: 'filter_region',
        title: 'Geographic Region',
        description: 'Analyze data by geographic location for regional insights',
        sourceVars: [regionVar.code],
        filterType: 'categorical',
        ui: { control: regionVar.cardinality > 10 ? 'select' : 'checkbox_group' },
        options: [],
        suitabilityScore: 9,
        rationale: `Geographic segmentation with ${regionVar.cardinality} regions enables location-based analysis and regional comparison.`
      });
    }

    // Income/Socioeconomic filters
    const incomePatterns = ['income', 'salary', 'wage', 'earning', 'socio', 'economic', 'ses', 'class', 'wealth', 'revenue'];
    const incomeVars = variables.filter(v => matchesPatterns(v, incomePatterns) && !usedVarCodes.has(v.code));
    if (incomeVars.length > 0) {
      const incomeVar = incomeVars[0];
      addFilter({
        id: 'filter_income',
        title: 'Income Level',
        description: 'Segment by income brackets for socioeconomic analysis',
        sourceVars: [incomeVar.code],
        filterType: 'ordinal',
        ui: { control: 'select' },
        options: [],
        suitabilityScore: 9,
        rationale: `Income segmentation is crucial for market analysis and purchasing power assessment. "${incomeVar.label}" provides ${incomeVar.cardinality} income brackets.`
      });
    }

    // Education filters
    const educationPatterns = ['education', 'edu', 'degree', 'school', 'university', 'diploma', 'graduate', 'college', 'academic'];
    const educationVars = variables.filter(v => matchesPatterns(v, educationPatterns) && !usedVarCodes.has(v.code));
    if (educationVars.length > 0) {
      const eduVar = educationVars[0];
      addFilter({
        id: 'filter_education',
        title: 'Education Level',
        description: 'Filter by educational attainment for demographic profiling',
        sourceVars: [eduVar.code],
        filterType: 'ordinal',
        ui: { control: 'select' },
        options: [],
        suitabilityScore: 8,
        rationale: `Education level correlates with many behavioral patterns. "${eduVar.label}" enables analysis across ${eduVar.cardinality} education categories.`
      });
    }

    // Employment/Occupation filters
    const employmentPatterns = ['employ', 'job', 'occupation', 'work', 'profession', 'career', 'labor', 'workforce'];
    const employmentVars = variables.filter(v => matchesPatterns(v, employmentPatterns) && !usedVarCodes.has(v.code));
    if (employmentVars.length > 0) {
      const empVar = employmentVars[0];
      addFilter({
        id: 'filter_employment',
        title: 'Employment Status',
        description: 'Segment by occupation or employment status',
        sourceVars: [empVar.code],
        filterType: 'categorical',
        ui: { control: empVar.cardinality > 8 ? 'select' : 'checkbox_group' },
        options: [],
        suitabilityScore: 8,
        rationale: `Employment status affects consumer behavior and preferences. "${empVar.label}" has ${empVar.cardinality} categories for workforce segmentation.`
      });
    }

    // Marital Status filters
    const maritalPatterns = ['marital', 'married', 'single', 'spouse', 'divorce', 'widow', 'partner'];
    const maritalVars = variables.filter(v => matchesPatterns(v, maritalPatterns) && !usedVarCodes.has(v.code));
    if (maritalVars.length > 0) {
      const maritalVar = maritalVars[0];
      addFilter({
        id: 'filter_marital',
        title: 'Marital Status',
        description: 'Filter by marital/family status',
        sourceVars: [maritalVar.code],
        filterType: 'categorical',
        ui: { control: 'checkbox_group' },
        options: [],
        suitabilityScore: 7,
        rationale: `Marital status influences household decisions and lifestyle patterns.`
      });
    }

    // ============================================
    // 2. BEHAVIORAL/ATTITUDINAL FILTERS
    // ============================================

    // Satisfaction filters
    const satisfactionPatterns = ['satisf', 'happy', 'content', 'rating', 'score', 'nps', 'recommend', 'loyalty', 'csat'];
    const satisfactionVars = variables.filter(v => 
      matchesPatterns(v, satisfactionPatterns) && 
      !usedVarCodes.has(v.code) && 
      v.cardinality >= 3 && v.cardinality <= 11
    );
    if (satisfactionVars.length > 0) {
      const satVar = satisfactionVars[0];
      addFilter({
        id: 'filter_satisfaction',
        title: 'Satisfaction Level',
        description: 'Filter by customer/respondent satisfaction scores',
        sourceVars: [satVar.code],
        filterType: 'ordinal',
        ui: { control: 'range_slider' },
        options: [],
        suitabilityScore: 9,
        rationale: `Satisfaction metrics are key performance indicators. "${satVar.label}" allows segmentation by satisfaction tiers.`
      });
    }

    // Frequency/Usage filters
    const frequencyPatterns = ['frequency', 'often', 'usage', 'use', 'times', 'regular', 'habit', 'routine'];
    const frequencyVars = variables.filter(v => matchesPatterns(v, frequencyPatterns) && !usedVarCodes.has(v.code));
    if (frequencyVars.length > 0) {
      const freqVar = frequencyVars[0];
      addFilter({
        id: 'filter_frequency',
        title: 'Usage Frequency',
        description: 'Segment by how often respondents use/engage',
        sourceVars: [freqVar.code],
        filterType: 'ordinal',
        ui: { control: 'select' },
        options: [],
        suitabilityScore: 8,
        rationale: `Usage frequency is critical for understanding engagement levels and user segmentation.`
      });
    }

    // Brand/Product awareness filters
    const brandPatterns = ['brand', 'product', 'aware', 'know', 'heard', 'recognition', 'familiarity', 'recall'];
    const brandVars = variables.filter(v => matchesPatterns(v, brandPatterns) && !usedVarCodes.has(v.code));
    if (brandVars.length > 0) {
      const brandVar = brandVars[0];
      addFilter({
        id: 'filter_brand',
        title: 'Brand Awareness',
        description: 'Filter by brand/product awareness or preference',
        sourceVars: [brandVar.code],
        filterType: 'categorical',
        ui: { control: brandVar.cardinality > 5 ? 'select' : 'checkbox_group' },
        options: [],
        suitabilityScore: 8,
        rationale: `Brand awareness segmentation enables competitive analysis and market positioning insights.`
      });
    }

    // Purchase/Buying behavior filters
    const purchasePatterns = ['purchase', 'buy', 'bought', 'spend', 'payment', 'order', 'transaction', 'checkout'];
    const purchaseVars = variables.filter(v => matchesPatterns(v, purchasePatterns) && !usedVarCodes.has(v.code));
    if (purchaseVars.length > 0) {
      const purchaseVar = purchaseVars[0];
      addFilter({
        id: 'filter_purchase',
        title: 'Purchase Behavior',
        description: 'Segment by purchasing patterns and behavior',
        sourceVars: [purchaseVar.code],
        filterType: 'categorical',
        ui: { control: 'select' },
        options: [],
        suitabilityScore: 8,
        rationale: `Purchase behavior is essential for customer value analysis and targeting strategies.`
      });
    }

    // Channel/Media preference filters
    const channelPatterns = ['channel', 'media', 'source', 'platform', 'social', 'tv', 'radio', 'internet', 'digital', 'online'];
    const channelVars = variables.filter(v => matchesPatterns(v, channelPatterns) && !usedVarCodes.has(v.code));
    if (channelVars.length > 0) {
      const channelVar = channelVars[0];
      addFilter({
        id: 'filter_channel',
        title: 'Channel Preference',
        description: 'Filter by preferred communication or media channels',
        sourceVars: [channelVar.code],
        filterType: 'multi_select',
        ui: { control: 'checkbox_group' },
        options: [],
        suitabilityScore: 7,
        rationale: `Channel preferences inform marketing strategy and communication planning.`
      });
    }

    // ============================================
    // 3. TIME-BASED FILTERS
    // ============================================

    // Date/Time filters
    const datePatterns = ['date', 'time', 'year', 'month', 'week', 'day', 'period', 'quarter', 'season', 'calendar'];
    const dateVars = variables.filter(v => matchesPatterns(v, datePatterns) && !usedVarCodes.has(v.code));
    if (dateVars.length > 0) {
      const dateVar = dateVars[0];
      addFilter({
        id: 'filter_time',
        title: 'Time Period',
        description: 'Filter by time period or date range',
        sourceVars: [dateVar.code],
        filterType: dateVar.type === 'numeric' ? 'date_range' : 'categorical',
        ui: { control: dateVar.type === 'numeric' ? 'date_picker' : 'select' },
        options: [],
        suitabilityScore: 7,
        rationale: `Time-based filtering enables trend analysis and period-over-period comparisons.`
      });
    }

    // ============================================
    // 4. SURVEY-SPECIFIC FILTERS
    // ============================================

    // Response quality filters (based on response rate)
    const highQualityVars = variables.filter(v => 
      v.responseRate >= 90 && 
      v.cardinality > 2 && 
      v.cardinality < 15 &&
      !usedVarCodes.has(v.code)
    );

    // Identify scale variables (1-5, 1-7, 1-10 scales)
    const scaleVars = variables.filter(v => 
      !usedVarCodes.has(v.code) &&
      (v.cardinality === 5 || v.cardinality === 7 || v.cardinality === 10 || v.cardinality === 11) &&
      v.type !== 'multiple_choice'
    );
    
    if (scaleVars.length > 0) {
      const scaleVar = scaleVars[0];
      addFilter({
        id: 'filter_scale',
        title: scaleVar.label.length > 35 ? scaleVar.label.substring(0, 35) + '...' : scaleVar.label,
        description: `Filter by ${scaleVar.cardinality}-point scale responses`,
        sourceVars: [scaleVar.code],
        filterType: 'ordinal',
        ui: { control: 'range_slider' },
        options: [],
        suitabilityScore: 7,
        rationale: `Scale variable with ${scaleVar.cardinality} points enables nuanced segmentation. Response rate: ${scaleVar.responseRate?.toFixed(0) || 0}%.`
      });
    }

    // ============================================
    // 5. MULTI-RESPONSE / GRID QUESTION FILTERS
    // ============================================

    // Detect grid questions (variables with similar prefixes like Q1_1, Q1_2, Q1_3)
    const varPrefixes = new Map<string, VariableSummary[]>();
    variables.forEach(v => {
      const match = v.code.match(/^([A-Za-z]+\d*)_/);
      if (match) {
        const prefix = match[1];
        if (!varPrefixes.has(prefix)) {
          varPrefixes.set(prefix, []);
        }
        varPrefixes.get(prefix)!.push(v);
      }
    });

    // Find grid questions with 3+ items
    const gridQuestions = Array.from(varPrefixes.entries())
      .filter(([prefix, vars]) => vars.length >= 3 && vars.length <= 20)
      .filter(([prefix, vars]) => !vars.some(v => usedVarCodes.has(v.code)));

    if (gridQuestions.length > 0) {
      const [prefix, gridVars] = gridQuestions[0];
      addFilter({
        id: 'filter_grid',
        title: `${gridVars[0].label.split(' ')[0] || prefix} Series`,
        description: `Multi-item question series with ${gridVars.length} items`,
        sourceVars: gridVars.map(v => v.code),
        filterType: 'multi_select',
        ui: { control: 'checkbox_group' },
        options: [],
        suitabilityScore: 7,
        rationale: `Grid question "${prefix}" contains ${gridVars.length} related items. Useful for cross-item analysis and pattern detection.`
      });
    }

    // ============================================
    // 6. HIGH-QUALITY CATEGORICAL VARIABLES
    // ============================================

    // Add remaining high-quality categorical variables
    const remainingCategorical = variables.filter(v => 
      !usedVarCodes.has(v.code) &&
      v.type === 'single_choice' &&
      v.cardinality >= 2 &&
      v.cardinality <= 20 &&
      v.responseRate >= 70
    ).sort((a, b) => (b.responseRate || 0) - (a.responseRate || 0));

    // Add up to 4 more categorical filters
    const maxAdditional = Math.min(4, 15 - filters.length);
    remainingCategorical.slice(0, maxAdditional).forEach((v, i) => {
      addFilter({
        id: `filter_cat_${i}`,
        title: v.label.length > 40 ? v.label.substring(0, 40) + '...' : v.label,
        description: `Categorical segmentation by ${v.code}`,
        sourceVars: [v.code],
        filterType: 'categorical',
        ui: { control: v.cardinality > 6 ? 'select' : 'checkbox_group' },
        options: [],
        suitabilityScore: 6 - Math.floor(i / 2),
        rationale: `High-quality variable with ${v.cardinality} categories and ${v.responseRate?.toFixed(0) || 0}% response rate. Suitable for detailed segmentation.`
      });
    });

    // ============================================
    // 7. NUMERIC RANGE FILTERS
    // ============================================

    const numericVars = variables.filter(v => 
      !usedVarCodes.has(v.code) &&
      v.type === 'numeric' &&
      v.cardinality > 10
    );

    if (numericVars.length > 0 && filters.length < 15) {
      const numVar = numericVars[0];
      addFilter({
        id: 'filter_numeric',
        title: numVar.label.length > 35 ? numVar.label.substring(0, 35) + '...' : numVar.label,
        description: 'Filter by numeric range',
        sourceVars: [numVar.code],
        filterType: 'numeric_range',
        ui: { control: 'range_slider' },
        options: [],
        suitabilityScore: 6,
        rationale: `Continuous numeric variable "${numVar.code}" enables range-based filtering for precise segmentation.`
      });
    }

    // ============================================
    // 8. FALLBACK: Ensure minimum filters
    // ============================================

    if (filters.length < 4 && variables.length > 0) {
      const fallbackVars = variables
        .filter(v => !usedVarCodes.has(v.code) && v.cardinality > 1 && v.cardinality < 50)
        .sort((a, b) => (b.responseRate || 0) - (a.responseRate || 0))
        .slice(0, 6 - filters.length);

      fallbackVars.forEach((v, i) => {
        addFilter({
          id: `filter_fallback_${i}`,
          title: v.label.length > 40 ? v.label.substring(0, 40) + '...' : v.label,
          description: `Filter by ${v.code}`,
          sourceVars: [v.code],
          filterType: 'categorical',
          ui: { control: v.cardinality > 6 ? 'select' : 'checkbox_group' },
          options: [],
          suitabilityScore: 5 - i,
          rationale: `Variable "${v.code}" has ${v.cardinality} unique values. Auto-detected as potentially useful for data exploration.`
        });
      });
    }

    // Sort filters by suitability score (highest first)
    filters.sort((a, b) => b.suitabilityScore - a.suitabilityScore);

    return { filters };
  }
}

export const geminiService = new GeminiService();