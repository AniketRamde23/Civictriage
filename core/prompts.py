"""
System and user prompts for CivicTriage LLM classification.
Includes few-shot multilingual examples (English, Hindi, Telugu) to guide the LLM
to return strict JSON with English labels regardless of input language.
"""

SYSTEM_PROMPT = """You are CivicTriage, an expert AI civic grievance triage assistant for Indian municipal corporations.
Your task is to analyze civic complaints submitted by citizens in English, Hindi, or Telugu.

You must ALWAYS output valid JSON adhering strictly to this schema:
{
  "emotion": "Angry" | "Anxious" | "Sad" | "Neutral",
  "priority": "High" | "Medium" | "Low",
  "category": "Water" | "Roads" | "Sanitation" | "Electricity" | "Other",
  "english_summary": "<Short 1-sentence summary of the grievance in clear English>",
  "reason": "<One to two sentences explaining why this priority level was assigned, focusing on safety or disruption>"
}

DEFINITIONS:
1. Priority Levels:
   - "High": Direct risk to life, acute electrical or open manhole hazards, active structural collapse, severe residential sewage/flood entry, immediate danger.
   - "Medium": Total disruption of essential services for days (no drinking water for 3+ days, power blackouts, uncollected garbage over 5+ days, deep road craters).
   - "Low": Minor cosmetic repairs, single dim/burnt bulb, routine tree trimming, minor non-hazardous cracks.

2. Emotion Labels:
   - "Angry": Outrage, threats of protest, harsh criticism of negligence.
   - "Anxious": Fear, worry for children/seniors, apprehension of accidents/diseases.
   - "Sad": Helplessness, suffering, despair over prolonged misery.
   - "Neutral": Polite, objective, or factual reporting.

3. Category Labels:
   - "Water": Piped drinking water, pipe bursts, water contamination, water pressure, tankers.
   - "Roads": Potholes, road cave-ins, footpaths, asphalt damage, speed breakers.
   - "Sanitation": Garbage accumulation, clogged sewers, drain overflow, foul smell, public hygiene.
   - "Electricity": Live wires, electric shocks, transformer sparks, power blackouts, street lights.
   - "Other": Parks, stray animals, encroachment, noise, fallen tree branches.

CRITICAL INSTRUCTIONS:
- You must understand text in English, Hindi (Devanagari), or Telugu script.
- Even if the input is in Hindi or Telugu, your output values MUST use English labels only (Angry, Anxious, Sad, Neutral / High, Medium, Low / Water, Roads, Sanitation, Electricity, Other).
- The "english_summary" must always be written in English.
- Do NOT include markdown formatting or backticks around the JSON. Output ONLY the raw JSON object.
"""

FEW_SHOT_EXAMPLES = [
    # English Examples
    {
        "input": "A high-tension electric wire snapped and fell into a water puddle outside our apartment gate! Sparks are flying everywhere and children are walking by!",
        "output": {
            "emotion": "Angry",
            "priority": "High",
            "category": "Electricity",
            "english_summary": "Live high-tension electric wire snapped into puddle near apartment gate sparking hazards.",
            "reason": "Exposed high-voltage wire in a water puddle creates an immediate risk of electrocution to pedestrians and children."
        }
    },
    {
        "input": "There is no drinking water supply in our colony for the last 4 days. Families are struggling to cook and drink.",
        "output": {
            "emotion": "Sad",
            "priority": "Medium",
            "category": "Water",
            "english_summary": "Total lack of drinking water supply for four consecutive days.",
            "reason": "Absence of basic drinking water for four days causes significant humanitarian distress and requires rapid resolution."
        }
    },
    {
        "input": "The street light bulb on pole number 15 is fused. Please replace it whenever convenient.",
        "output": {
            "emotion": "Neutral",
            "priority": "Low",
            "category": "Electricity",
            "english_summary": "Fused street light bulb on pole 15 requesting routine replacement.",
            "reason": "A single burnt streetlight bulb poses no immediate safety risk and can be handled during scheduled maintenance."
        }
    },

    # Hindi Examples
    {
        "input": "मेन रोड पर गहरा मैनहोल खुला पड़ा है! कल रात एक बाइक सवार उसमें गिरते-गिरते बचा। तुरंत ढक्कन लगवाएं वरना किसी की जान चली जाएगी!",
        "output": {
            "emotion": "Anxious",
            "priority": "High",
            "category": "Sanitation",
            "english_summary": "Open unguarded manhole on main road posing fatal danger to commuters.",
            "reason": "An open manhole on a busy road poses an acute risk of fatal accidents to motorists and pedestrians."
        }
    },
    {
        "input": "हमारी गली में पिछले 8 दिनों से कूड़ा उठाने वाली गाड़ी नहीं आई है। कूड़े के ढेर से असहनीय दुर्गंध आ रही है और मक्खियां भिनभिना रही हैं।",
        "output": {
            "emotion": "Angry",
            "priority": "Medium",
            "category": "Sanitation",
            "english_summary": "Garbage uncollected for 8 days causing unbearable stench and vector breeding.",
            "reason": "Prolonged pile-up of domestic waste for over a week causes health hazards and pest breeding requiring prompt clearance."
        }
    },
    {
        "input": "पार्क के जॉगिंग ट्रैक के किनारे घास काफी बढ़ गई है, कृपया माली से कटाई करवा दें।",
        "output": {
            "emotion": "Neutral",
            "priority": "Low",
            "category": "Other",
            "english_summary": "Overgrown grass along park jogging track requesting routine trimming.",
            "reason": "Routine landscape maintenance for a public park that carries no urgent risk or severe service breakdown."
        }
    },

    # Telugu Examples
    {
        "input": "మా వీధిలో 11 కేవీ కరెంట్ వైరు తెగి నీటి గుంటలో పడింది! తీవ్రమైన మంటలు వస్తున్నాయి, ప్రాణాపాయం ఉంది త్వరగా రండి!",
        "output": {
            "emotion": "Angry",
            "priority": "High",
            "category": "Electricity",
            "english_summary": "Snapped 11kV live power cable sparking in water puddle posing mortal danger.",
            "reason": "Live high-voltage wire in water creates an imminent fatal shock and fire hazard requiring emergency shutdown."
        }
    },
    {
        "input": "నాలుగు రోజులుగా మా ప్రాంతంలో మంచినీటి సరఫరా పూర్తిగా నిలిచిపోయింది. వంటకు, తాగడానికి నీరు లేక ప్రజలు తీవ్ర ఇబ్బందులు పడుతున్నారు.",
        "output": {
            "emotion": "Sad",
            "priority": "Medium",
            "category": "Water",
            "english_summary": "Complete failure of drinking water supply for four days causing public distress.",
            "reason": "Total stoppage of potable water for four days severely disrupts daily living and necessitates intervention within 24-72 hours."
        }
    },
    {
        "input": "రోడ్డు పక్కన ఉన్న చిన్న డ్రైనేజీ స్లాబ్ పై పగులు వచ్చింది, సాధారణ మరమ్మతులు చేయించండి.",
        "output": {
            "emotion": "Neutral",
            "priority": "Low",
            "category": "Sanitation",
            "english_summary": "Minor crack on roadside drain slab requiring routine repair.",
            "reason": "Minor structural fissure on a roadside slab with no immediate obstruction or peril to pedestrians."
        }
    }
]


def build_triage_prompt(grievance_text: str, detected_lang: str) -> str:
    """Build user prompt combining few-shot multilingual examples with the input grievance."""
    few_shot_str = ""
    for idx, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        import json
        few_shot_str += f"\nExample {idx}:\nInput: \"{ex['input']}\"\nOutput: {json.dumps(ex['output'], ensure_ascii=False)}\n"

    prompt = f"""Here are reference examples of civic grievances and their exact JSON classifications:{few_shot_str}

Now classify the following citizen grievance:
Detected Language: {detected_lang}
Input Grievance Text:
\"\"\"{grievance_text}\"\"\"

Return ONLY the raw JSON object without markdown fences.
"""
    return prompt
