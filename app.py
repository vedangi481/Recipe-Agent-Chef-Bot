"""
Recipe Preparation Agent — Flask Application Entry Point
IBM watsonx.ai + Granite + ChromaDB RAG Pipeline
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

from rag_pipeline import RecipeRAGPipeline
from watsonx_client import WatsonxClient

# ------------------------------------------------------------------ #
# Logging configuration                                               #
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Flask app setup                                                     #
# ------------------------------------------------------------------ #
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())

# ------------------------------------------------------------------ #
# Global singletons                                                   #
# ------------------------------------------------------------------ #
rag: RecipeRAGPipeline = RecipeRAGPipeline()
llm: WatsonxClient     = WatsonxClient()

# In-memory storage for recipe history and favorites
# In production, replace with a real database (SQLite / PostgreSQL)
recipe_history: Dict[str, List[Dict]] = {}
recipe_favorites: Dict[str, List[Dict]] = {}


# ------------------------------------------------------------------ #
# Application startup                                                 #
# ------------------------------------------------------------------ #
def startup() -> None:
    """Initialize RAG pipeline on first use."""
    logger.info("Starting Recipe Preparation Agent …")
    try:
        rag.initialize()
        logger.info("RAG pipeline ready. Demo mode: %s", llm.is_demo_mode())
    except Exception as exc:
        logger.error("RAG initialization error: %s", exc)


# ------------------------------------------------------------------ #
# Helper utilities                                                    #
# ------------------------------------------------------------------ #

def _get_session_id() -> str:
    """Return (and create if needed) a session identifier."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def _detect_query_intent(message: str) -> Dict[str, Any]:
    """
    Simple keyword-based intent detection to route retrieval.
    Returns hints used to pick the right RAG collections.
    """
    msg = message.lower()
    intent = {
        "is_substitution":  any(w in msg for w in ["substitute", "replace", "instead of", "without", "no", "alternative"]),
        "is_dietary":       any(w in msg for w in ["vegetarian", "vegan", "jain", "gluten", "diabetic", "protein", "low-carb", "keto", "allergy"]),
        "is_technique":     any(w in msg for w in ["how to", "technique", "method", "cook", "fry", "bake", "boil", "knead"]),
        "is_nutrition":     any(w in msg for w in ["calories", "protein", "nutrition", "healthy", "fat", "carbs", "vitamins", "minerals"]),
        "is_leftover":      any(w in msg for w in ["leftover", "remaining", "already have", "use up", "waste"]),
        "is_quick":         any(w in msg for w in ["quick", "fast", "minutes", "easy", "simple", "under 20", "under 30"]),
        "is_ingredient_query": any(w in msg for w in ["i have", "using", "with", "can i make", "what can i cook", "recipe for"]),
    }
    return intent


def _build_rag_query(message: str, ingredients: List[str], dietary_filters: List[str]) -> str:
    """Construct an enhanced query string for RAG retrieval."""
    parts = [message]
    if ingredients:
        parts.append(f"ingredients: {', '.join(ingredients)}")
    if dietary_filters:
        parts.append(f"dietary: {', '.join(dietary_filters)}")
    return " | ".join(parts)


def _select_collections(intent: Dict[str, Any]) -> List[str]:
    """Choose which ChromaDB collections to query based on intent."""
    if intent["is_substitution"]:
        return ["substitutions", "recipes"]
    if intent["is_dietary"]:
        return ["dietary", "recipes", "nutrition"]
    if intent["is_technique"]:
        return ["techniques", "recipes"]
    if intent["is_nutrition"]:
        return ["nutrition", "dietary"]
    # Default: search all
    return ["recipes", "techniques", "substitutions", "nutrition", "dietary"]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def index():
    """Main application page."""
    session_id = _get_session_id()
    return render_template(
        "index.html",
        session_id=session_id,
        demo_mode=llm.is_demo_mode(),
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Accepts a user message, retrieves context from RAG, and generates a response.
    """
    try:
        data = request.get_json(force=True)
        message         = (data.get("message") or "").strip()
        ingredients     = data.get("ingredients") or []
        dietary_filters = data.get("dietary_filters") or []
        history         = data.get("history") or []

        if not message:
            return jsonify({"error": "Message is required."}), 400

        session_id = _get_session_id()

        # --- Intent detection ---------------------------------------- #
        intent = _detect_query_intent(message)
        collections = _select_collections(intent)

        # --- Build enriched RAG query --------------------------------- #
        rag_query = _build_rag_query(message, ingredients, dietary_filters)

        # --- Retrieve context ----------------------------------------- #
        context = rag.retrieve(
            query=rag_query,
            n_results=4,
            collections=collections,
        )

        # If ingredient-focused, also do targeted ingredient retrieval
        if ingredients and (intent["is_ingredient_query"] or intent["is_leftover"]):
            extra = rag.retrieve_by_ingredients(ingredients, n_results=3)
            context = context + "\n\n---\n\n" + extra if extra else context

        # --- Add dietary filter context ------------------------------- #
        for diet in dietary_filters:
            extra = rag.retrieve_dietary(diet)
            if extra:
                context = context + "\n\n---\n\n" + extra

        # --- Augment message with filters ----------------------------- #
        augmented_message = message
        if dietary_filters:
            augmented_message += f"\n[Dietary preferences: {', '.join(dietary_filters)}]"
        if ingredients:
            augmented_message += f"\n[Available ingredients: {', '.join(ingredients)}]"

        # --- Generate response --------------------------------------- #
        response = llm.generate(
            user_message=augmented_message,
            context=context,
            history=history,
        )

        # --- Save to history ------------------------------------------ #
        if session_id not in recipe_history:
            recipe_history[session_id] = []
        recipe_history[session_id].append({
            "id":         str(uuid.uuid4()),
            "timestamp":  datetime.now().isoformat(),
            "user":       message,
            "assistant":  response,
            "ingredients": ingredients,
            "dietary":    dietary_filters,
        })

        # Keep last 50 messages per session
        recipe_history[session_id] = recipe_history[session_id][-50:]

        return jsonify({
            "response":  response,
            "session_id": session_id,
            "demo_mode":  llm.is_demo_mode(),
        })

    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        return jsonify({"error": f"An internal error occurred: {exc}"}), 500


@app.route("/api/substitution", methods=["POST"])
def substitution():
    """Get ingredient substitution recommendations."""
    try:
        data = request.get_json(force=True)
        ingredient = (data.get("ingredient") or "").strip()

        if not ingredient:
            return jsonify({"error": "Ingredient name is required."}), 400

        context = rag.retrieve_substitutions(ingredient)
        message = f"What are the best substitutes for {ingredient} in cooking? Explain why each works and any flavor or texture differences."
        response = llm.generate(user_message=message, context=context)

        return jsonify({"response": response, "ingredient": ingredient})

    except Exception as exc:
        logger.exception("Substitution endpoint error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/nutrition", methods=["POST"])
def nutrition():
    """Get nutritional information for a recipe or ingredients."""
    try:
        data  = request.get_json(force=True)
        query = (data.get("query") or "").strip()

        if not query:
            return jsonify({"error": "Query is required."}), 400

        context  = rag.retrieve(query=query, n_results=4, collections=["nutrition", "recipes"])
        message  = f"Provide detailed nutritional information for: {query}. Include calories, macros, vitamins, and minerals."
        response = llm.generate(user_message=message, context=context)

        return jsonify({"response": response})

    except Exception as exc:
        logger.exception("Nutrition endpoint error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    """Return the chat/recipe history for the current session."""
    session_id = _get_session_id()
    history = recipe_history.get(session_id, [])
    return jsonify({"history": history[-20:]})  # return last 20


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """Clear chat history for the current session."""
    session_id = _get_session_id()
    recipe_history.pop(session_id, None)
    return jsonify({"message": "History cleared."})


@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    """Return saved favorite recipes for the current session."""
    session_id = _get_session_id()
    return jsonify({"favorites": recipe_favorites.get(session_id, [])})


@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    """Save a recipe to favorites."""
    try:
        data       = request.get_json(force=True)
        session_id = _get_session_id()
        recipe = {
            "id":        str(uuid.uuid4()),
            "saved_at":  datetime.now().isoformat(),
            "title":     data.get("title", "Recipe"),
            "content":   data.get("content", ""),
            "tags":      data.get("tags", []),
        }
        if session_id not in recipe_favorites:
            recipe_favorites[session_id] = []
        recipe_favorites[session_id].append(recipe)
        return jsonify({"message": "Recipe saved to favorites!", "recipe": recipe})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/favorites/<recipe_id>", methods=["DELETE"])
def remove_favorite(recipe_id: str):
    """Remove a recipe from favorites."""
    session_id = _get_session_id()
    favorites  = recipe_favorites.get(session_id, [])
    recipe_favorites[session_id] = [f for f in favorites if f["id"] != recipe_id]
    return jsonify({"message": "Recipe removed from favorites."})


@app.route("/api/quick-recipes", methods=["POST"])
def quick_recipes():
    """Get recipes based on available ingredients."""
    try:
        data        = request.get_json(force=True)
        ingredients = data.get("ingredients") or []
        dietary     = data.get("dietary") or []
        time_limit  = data.get("time_limit")  # minutes

        if not ingredients:
            return jsonify({"error": "Ingredient list is required."}), 400

        query_parts = [f"I have these ingredients: {', '.join(ingredients)}. Suggest recipes."]
        if dietary:
            query_parts.append(f"Dietary: {', '.join(dietary)}")
        if time_limit:
            query_parts.append(f"Must be ready in under {time_limit} minutes")

        full_query = " ".join(query_parts)
        context    = rag.retrieve(query=full_query, n_results=5, collections=["recipes", "techniques"])
        response   = llm.generate(user_message=full_query, context=context)

        return jsonify({"response": response, "ingredients": ingredients})

    except Exception as exc:
        logger.exception("Quick recipes error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/favicon.ico")
def favicon():
    """Serve an inline SVG favicon — eliminates the 404 log noise."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<text y="26" font-size="28">👨\u200d🍳</text>'
        "</svg>"
    )
    return svg, 200, {"Content-Type": "image/svg+xml", "Cache-Control": "public,max-age=86400"}


@app.route("/api/status", methods=["GET"])
def status():
    """Health-check endpoint."""
    return jsonify({
        "status":      "ok",
        "demo_mode":   llm.is_demo_mode(),
        "rag_status":  rag.get_status(),
        "model_id":    os.getenv("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct"),
    })


@app.route("/api/reload-kb", methods=["POST"])
def reload_kb():
    """Force-reload the knowledge base into ChromaDB."""
    try:
        rag.initialize(force_reload=True)
        return jsonify({"message": "Knowledge base reloaded successfully.", "status": rag.get_status()})
    except Exception as exc:
        logger.exception("KB reload error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ------------------------------------------------------------------ #
# Entry point                                                         #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    startup()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    logger.info("Starting Flask server on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
