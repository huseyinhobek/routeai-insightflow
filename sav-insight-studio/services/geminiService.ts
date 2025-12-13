import { GoogleGenAI, Type, Schema } from "@google/genai";
import { DatasetMeta, VariableSummary, SmartFilterResponse } from "../types";

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
  private client: GoogleGenAI;

  constructor() {
    this.client = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
  }

  /**
   * Suggests smart filters based on dataset metadata.
   * Note: We do NOT send respondent-level data, only metadata (labels, types).
   */
  async suggestSmartFilters(dataset: DatasetMeta): Promise<SmartFilterResponse> {
    if (!process.env.API_KEY) {
      console.warn("Gemini API Key missing. Returning mock data or empty.");
      return { filters: [] };
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
      throw error;
    }
  }
}

export const geminiService = new GeminiService();