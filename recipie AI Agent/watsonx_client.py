"""
IBM watsonx.ai Granite Client — Recipe Preparation Agent
Handles all interactions with IBM Granite foundation models via watsonx.ai.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ======================================================================= #
# AGENT INSTRUCTIONS — Customize personality, style, and safety rules here #
# ======================================================================= #
AGENT_INSTRUCTIONS = """
You are ChefBot, an AI-powered Recipe Preparation Assistant powered by IBM Granite.

## Personality & Expertise
- Friendly, encouraging, and patient cooking guide for all skill levels
- Deep knowledge of Indian and international cuisines
- Expert in vegetarian, vegan, Jain, gluten-free, diabetic-friendly, and other dietary needs
- Bilingual: respond in the same language the user uses (English or Hindi/Hinglish)

## Core Responsibilities
1. ALWAYS use the provided context from the knowledge base — avoid hallucinations
2. Recommend recipes based on ingredients the user ALREADY HAS, not what they need to buy
3. Explain ingredient substitutions with clear reasons and taste/texture implications
4. Adapt recipes for missing ingredients while preserving taste and nutrition
5. Flag common food allergens proactively (nuts, dairy, gluten, eggs)
6. Give clear, numbered step-by-step cooking instructions
7. Include estimated cooking time and serving size in every recommendation
8. Suggest leftover usage and food waste reduction tips when relevant

## Response Style
- Use clear numbered lists for recipe steps
- Bold key actions and important warnings with **asterisks**
- Keep instructions beginner-friendly but add pro-tips for advanced cooks
- Always end with storage tips and serving suggestions
- When answering in Hindi/Hinglish, use simple conversational language

## Safety Precautions
- Always mention food safety (proper cooking temperatures, storage times)
- Warn about cross-contamination when cooking for allergy sufferers
- Remind users to wash hands and produce before cooking
- Note if a dish contains common allergens

## Dietary Guidance
- Vegetarian (no meat/fish), Vegan (no animal products), Jain (no root vegetables)
- Gluten-Free: Avoid wheat, barley, rye
- Diabetic-Friendly: Recommend low-GI foods, portion control
- High-Protein: Focus on legumes, dairy, eggs, tofu
- Low-Carb: Reduce grains and starchy vegetables

## Response Format for Recipe Requests
1. 🍽️ Recipe Name (+ Hindi name if Indian dish)
2. ⏱️ Time & Difficulty
3. 🥗 Nutrition highlights
4. 📝 Ingredients (note any substitutions for missing items)
5. 👨‍🍳 Step-by-step instructions
6. 💡 Pro tips & variations
7. 🛡️ Allergen & safety notes (if relevant)

## Language Support
- English: Default language
- Hindi (हिंदी): If user writes in Hindi/Devanagari, respond in Hindi
- Hinglish: If user mixes Hindi and English, respond in Hinglish
"""
# ======================================================================= #
# END OF AGENT INSTRUCTIONS                                                 #
# ======================================================================= #


class WatsonxClient:
    """
    Client for IBM watsonx.ai Granite models.
    Falls back to a mock/demo mode if credentials are not configured.
    """

    # Model IDs available on IBM watsonx.ai
    GRANITE_MODELS = {
        "granite-3-8b-instruct":    "ibm/granite-3-8b-instruct",
        "granite-3-2b-instruct":    "ibm/granite-3-2b-instruct",
        "granite-13b-instruct-v2":  "ibm/granite-13b-instruct-v2",
    }

    def __init__(self):
        self.api_key    = os.getenv("IBM_API_KEY", "")
        self.project_id = os.getenv("IBM_PROJECT_ID", "")
        self.watsonx_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id   = os.getenv("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")
        self._model     = None
        self._demo_mode = False
        self._setup_client()

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    def _setup_client(self) -> None:
        """Initialize the WatsonX model client."""
        if not self.api_key or not self.project_id:
            logger.warning(
                "IBM credentials not configured — running in DEMO MODE. "
                "Set IBM_API_KEY and IBM_PROJECT_ID in .env to use real Granite models."
            )
            self._demo_mode = True
            return

        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai.foundation_models.schema import TextGenParameters

            credentials = Credentials(
                url=self.watsonx_url,
                api_key=self.api_key,
            )
            params = TextGenParameters(
                max_new_tokens=1024,
                min_new_tokens=20,
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
            )
            self._model = ModelInference(
                model_id=self.model_id,
                credentials=credentials,
                project_id=self.project_id,
                params=params,
            )
            logger.info("watsonx.ai client initialized with model: %s", self.model_id)
        except ImportError:
            logger.warning("ibm-watsonx-ai package not installed — running in DEMO MODE.")
            self._demo_mode = True
        except Exception as exc:
            logger.error("Failed to initialize watsonx client: %s — running in DEMO MODE.", exc)
            self._demo_mode = True

    # ------------------------------------------------------------------ #
    # Generation                                                           #
    # ------------------------------------------------------------------ #

    def generate(self, user_message: str, context: str = "", history: Optional[list] = None) -> str:
        """
        Generate a recipe response using Granite with RAG context.

        Args:
            user_message: The user's query.
            context:      Retrieved knowledge-base context.
            history:      Previous conversation turns [{role, content}, ...].

        Returns:
            The assistant's response as a string.
        """
        if self._demo_mode:
            return self._demo_response(user_message, context)

        prompt = self._build_prompt(user_message, context, history)

        try:
            response = self._model.generate_text(prompt=prompt)
            # SDK 1.3+ returns a dict: {"generated_text": "...", "stop_reason": "...", ...}
            # SDK 1.1 returned a plain string. Handle both.
            if isinstance(response, dict):
                text = response.get("generated_text") or response.get("results", [{}])[0].get("generated_text", "")
            elif isinstance(response, str):
                text = response
            else:
                text = str(response)
            return text.strip()
        except Exception as exc:
            logger.error("Generation error: %s", exc)
            err_str = str(exc)
            # Friendly message for common IBM Cloud errors
            if "Inactive" in err_str or "invalid_instance_status" in err_str:
                user_msg = (
                    "⚠️ **IBM watsonx.ai instance is inactive.**\n\n"
                    "Your IBM Cloud Watson Machine Learning service needs to be reactivated:\n"
                    "1. Go to **https://cloud.ibm.com** → Resource List\n"
                    "2. Find your Watson Machine Learning instance\n"
                    "3. Click **Resume / Activate**\n\n"
                    "While you fix that, I'll use the built-in demo responses.\n\n"
                )
                return user_msg + self._demo_response(user_message, context)
            if "403" in err_str or "401" in err_str or "authentication" in err_str.lower():
                return (
                    "⚠️ **Authentication error (403/401).**\n\n"
                    "Your IBM API key may have expired. "
                    "Generate a new one at https://cloud.ibm.com/iam/apikeys and update `.env`.\n\n"
                ) + self._demo_response(user_message, context)
            return (
                f"⚠️ **watsonx.ai error:** {exc}\n\n"
                "Falling back to demo response:\n\n"
            ) + self._demo_response(user_message, context)

    def _build_prompt(
        self,
        user_message: str,
        context: str,
        history: Optional[list] = None,
    ) -> str:
        """
        Build a chat prompt in the correct format for the active model.
        - Llama 3.x  → <|begin_of_text|><|start_header_id|>system<|end_header_id|>…
        - Granite 3  → <|system|>…<|user|>…<|assistant|>
        """
        history = history or []

        system_content = AGENT_INSTRUCTIONS
        if context:
            system_content += f"\n\n## Retrieved Knowledge Base Context\n{context[:3000]}"

        is_llama = "llama" in self.model_id.lower()

        if is_llama:
            # ── Llama 3 instruct chat template ──────────────────────────
            prompt = "<|begin_of_text|>"
            prompt += (
                "<|start_header_id|>system<|end_header_id|>\n\n"
                f"{system_content}<|eot_id|>"
            )
            for turn in history[-6:]:
                role    = turn.get("role", "user")
                content = turn.get("content", "")
                prompt += (
                    f"<|start_header_id|>{role}<|end_header_id|>\n\n"
                    f"{content}<|eot_id|>"
                )
            prompt += (
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"{user_message}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n\n"
            )
        else:
            # ── IBM Granite 3 chat template ──────────────────────────────
            prompt = f"<|system|>\n{system_content}\n"
            for turn in history[-6:]:
                role    = turn.get("role", "user")
                content = turn.get("content", "")
                prompt += f"<|{role}|>\n{content}\n"
            prompt += f"<|user|>\n{user_message}\n<|assistant|>\n"

        return prompt

    # ------------------------------------------------------------------ #
    # Demo mode (no IBM credentials)                                      #
    # ------------------------------------------------------------------ #

    def _demo_response(self, user_message: str, context: str) -> str:
        """
        Return a structured demo response based on retrieved context.
        Used when IBM credentials are not available.
        """
        msg = user_message.lower()
        ctx_preview = context[:500] if context else ""

        if any(w in msg for w in ["potato", "aloo", "आलू"]):
            return (
                "🍽️ **Aloo Matar (Potato & Peas Curry)**\n\n"
                "⏱️ 40 mins | 🟢 Easy | 🌿 Vegetarian & Gluten-Free\n\n"
                "**Nutrition:** ~180 cal | 5g protein | 32g carbs | 5g fat\n\n"
                "**Ingredients:** Potatoes, green peas, onion, tomatoes, cumin, turmeric, garam masala\n\n"
                "**Steps:**\n"
                "1. Heat oil, add cumin seeds until they splutter\n"
                "2. Sauté onions until golden (8-10 min)\n"
                "3. Add tomatoes + spices, cook until oil separates\n"
                "4. Add potato cubes, cover & cook 10 min on medium heat\n"
                "5. Add peas, cook 5 more minutes\n"
                "6. Garnish with fresh coriander\n\n"
                "💡 **Tip:** Mash a few potato pieces to thicken the gravy naturally!\n\n"
                "🛡️ **Allergen note:** Dairy-free, gluten-free, nut-free\n\n"
                "*(Demo mode — set IBM_API_KEY in .env for full Granite AI responses)*"
            )
        elif any(w in msg for w in ["paneer", "पनीर", "spinach", "palak", "पालक"]):
            return (
                "🍽️ **Palak Paneer (Spinach & Cottage Cheese)**\n\n"
                "⏱️ 40 mins | 🟡 Medium | 🌿 Vegetarian, High-Protein\n\n"
                "**Nutrition:** ~280 cal | 16g protein | 12g carbs | 19g fat\n\n"
                "**Steps:**\n"
                "1. Blanch spinach 2 minutes, then blend to smooth puree\n"
                "2. Cook onion-tomato-spice base until oil separates\n"
                "3. Add spinach puree, simmer 5 minutes\n"
                "4. Add paneer cubes, simmer 3-4 minutes\n"
                "5. Finish with cream and garam masala\n\n"
                "💡 **Tip:** Blanching + ice bath preserves the vibrant green color!\n\n"
                "*(Demo mode — set IBM_API_KEY in .env for full Granite AI responses)*"
            )
        elif any(w in msg for w in ["rice", "leftover", "चावल"]):
            return (
                "🍽️ **Tomato Rice / Vegetable Fried Rice**\n\n"
                "⏱️ 25-30 mins | 🟢 Easy | 🌱 Vegan-friendly\n\n"
                "**For leftover rice, try:**\n"
                "- **Tomato Rice** (South Indian): Mustard seeds + curry leaves + tomatoes\n"
                "- **Vegetable Fried Rice**: Garlic + mixed veggies + soy sauce (Indo-Chinese)\n"
                "- **Khichdi variant**: Rice + dal + simple tempering\n\n"
                "💡 Cold, day-old rice works **best** for fried rice — less sticky!\n\n"
                "*(Demo mode — set IBM_API_KEY in .env for full Granite AI responses)*"
            )
        elif any(w in msg for w in ["egg", "अंडा", "substitute", "replace"]):
            return (
                "🥚 **Egg Substitution Guide**\n\n"
                "For **binding** (cakes, cookies, muffins):\n"
                "- **Flax egg**: 1 tbsp ground flaxseed + 3 tbsp water (rest 5 min) ✅ Best all-rounder\n"
                "- **Chia egg**: 1 tbsp chia seeds + 3 tbsp water\n"
                "- **Applesauce**: 1/4 cup — adds moisture\n\n"
                "For **scrambled eggs / bhurji**:\n"
                "- **Tofu scramble**: Crumble firm tofu + turmeric + black salt (kala namak for egg flavor)\n\n"
                "For **egg wash** (pastry sheen):\n"
                "- Milk or plant milk brushed on\n\n"
                "💡 **Black salt (kala namak)** has a sulfurous egg-like taste — great for vegan recipes!\n\n"
                "*(Demo mode — set IBM_API_KEY in .env for full Granite AI responses)*"
            )
        else:
            snippet = f"\n\n*Relevant knowledge found:*\n{ctx_preview[:300]}..." if ctx_preview else ""
            return (
                f"👨‍🍳 I'm ChefBot, your AI Recipe Assistant!\n\n"
                f"You asked: *\"{user_message}\"*\n\n"
                f"I have access to a comprehensive recipe knowledge base covering Indian and international dishes, "
                f"cooking techniques, ingredient substitutions, nutrition guides, and dietary recommendations.\n\n"
                f"**Try asking me:**\n"
                f"- 'I have potatoes, onions, and tomatoes — what can I cook?'\n"
                f"- 'Suggest a high-protein vegetarian dinner'\n"
                f"- 'How do I replace eggs in a recipe?'\n"
                f"- 'Give me gluten-free breakfast ideas'\n"
                f"- 'What can I make with leftover rice?'{snippet}\n\n"
                f"*(Demo mode — configure IBM_API_KEY in .env to use IBM Granite AI)*"
            )

    def is_demo_mode(self) -> bool:
        return self._demo_mode
