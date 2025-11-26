from fastapi import FastAPI, HTTPException           # FastAPI server + error handling
from fastapi.middleware.cors import CORSMiddleware   # Allows frontend or CLI to call API
import json                                          # For parsing model JSON

#noa adds
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
#after noa adds

# Import the data models we defined separately
from .models import (
    ParseRecipeRequest,
    ParseRecipeResponse,
    Step,
    AskRequest,
    AskResponse,
    GenerateRecipeRequest,
    GenerateRecipeResponse,
)

# Import our helper that calls the Ollama model
from .ollama_client import ollama_chat

# Create the FastAPI app object
app = FastAPI(
    title="KitchenBuddy",
    description="Interactive step-by-step cooking and recipe assistant using Ollama.",
    version="0.2.0",
)

# Allow all cross-origin requests (useful for future web frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#noa adds
# Mount frontend folder so FastAPI can serve your HTML/CSS/JS
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = frontend_path / "index.html"
    return index_file.read_text(encoding="utf-8")


@app.get("/cook", response_class=HTMLResponse)
async def serve_cook():
    cook_file = frontend_path / "cook.html"
    return cook_file.read_text(encoding="utf-8")


@app.get("/recipe", response_class=HTMLResponse)
async def serve_mealplanner():
    recipe_file = frontend_path / "recipe.html"
    return recipe_file.read_text(encoding="utf-8")


@app.get("/ask", response_class=HTMLResponse)
async def serve_ask():
    ask_file = frontend_path / "ask.html"
    return ask_file.read_text(encoding="utf-8")
#noa adds end

# ---------- Small helper functions ----------

def is_ingredient_style_question(question: str) -> bool:
    """
    Heuristic to detect when the user is asking something like:
    'I have X and Y, what can I cook?'
    """
    q = question.lower()
    triggers = [
        "what can i cook with",
        "what can i make with",
        "what can i do with",
        "i have ",
        "ingredients:",
        "use these ingredients",
    ]
    return any(t in q for t in triggers)


# ---------- Health check ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- /parse_recipe ----------

@app.post("/parse_recipe", response_model=ParseRecipeResponse)
def parse_recipe(req: ParseRecipeRequest):
    # Instructions we give the model before the user recipe
    system_prompt = (
        "You are KitchenBuddy, a helpful cooking assistant.\n"
        "You will receive a recipe as free text.\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  \"title\": \"Recipe title or null\",\n'
        '  \"steps\": [\n'
        '    {\"number\": 1, \"instruction\": \"First short step\"},\n'
        '    {\"number\": 2, \"instruction\": \"Second short step\"}\n'
        "  ]\n"
        "}\n"
        "Each instruction must be short, clear, and executable.\n"
        "Do not include anything outside the JSON object."
    )

    # User message containing the actual recipe text
    user_prompt = f"Here is the recipe:\n\n{req.recipe_text}"

    # Build chat messages for the model
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call the model and get raw text back
    raw = ollama_chat(messages)

    # Try to read the JSON the model produced
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Sometimes model wraps JSON with extra text → extract between braces
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise HTTPException(status_code=500, detail="Invalid JSON from model.")
        parsed = json.loads(raw[start : end + 1])

    # Validate the JSON has a "steps" list
    if "steps" not in parsed or not isinstance(parsed["steps"], list):
        raise HTTPException(status_code=500, detail="Model JSON missing 'steps' list.")

    # Convert raw step dicts to Step objects
    steps = [Step(**s) for s in parsed["steps"]]
    title = parsed.get("title")

    # Return parsed recipe
    return ParseRecipeResponse(title=title, steps=steps)


# ---------- /ask ----------

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """
    Answer a user's question.
    - If it's about ingredients / 'what can I cook with X', we treat it as a
      general recipe suggestion question.
    - Otherwise, we treat it as a question about the current recipe.
    """

    # Check whether the question is more about ingredients / general cooking
    if is_ingredient_style_question(req.question):
        # Ingredient-style / general cooking question mode
        system_prompt = (
            "You are KitchenBuddy, a creative but practical cooking assistant.\n"
            "The user is asking for recipe ideas or cooking suggestions based on "
            "ingredients or general kitchen questions.\n"
            "Answer with clear, helpful suggestions. You do NOT need to stick to "
            "the current recipe steps."
        )

        user_prompt = (
            "The user is currently cooking something else, but now asks a new, "
            "independent question about ingredients or recipes.\n\n"
            f"USER QUESTION:\n{req.question}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        answer = ollama_chat(messages)
        return AskResponse(answer=answer)

    # Otherwise: normal recipe-related Q&A mode
    step_descriptions = "\n".join(
        f"{s.number}. {s.instruction}" for s in req.all_steps
    )

    system_prompt = (
        "You are KitchenBuddy, a friendly cooking coach.\n"
        "You help the user understand and execute the recipe.\n"
        "Answer briefly and clearly.\n"
        "If the user asks for substitutions, suggest common options.\n"
        "If the question concerns food safety, be conservative and careful.\n"
    )

    user_prompt = (
        f"RECIPE STEPS:\n{step_descriptions}\n\n"
        f"CURRENT STEP:\n{req.current_step.number}. {req.current_step.instruction}\n\n"
        f"USER QUESTION:\n{req.question}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    answer = ollama_chat(messages)
    return AskResponse(answer=answer)


# ---------- /generate_recipe ----------

@app.post("/generate_recipe", response_model=GenerateRecipeResponse)
def generate_recipe(req: GenerateRecipeRequest):
    """
    Generate a structured recipe based on a list of ingredients
    (and optional preferences like vegetarian, quick, etc.).
    """

    system_prompt = (
        "You are KitchenBuddy, an expert recipe generator.\n"
        "The user will give you a list of ingredients (and maybe some preferences).\n"
        "You MUST respond ONLY with valid JSON using this exact structure:\n"
        "{\n"
        '  \"title\": \"Recipe title\",\n'
        '  \"description\": \"Short description of the dish\",\n'
        '  \"ingredients_list\": [\n'
        '    \"ingredient 1\",\n'
        '    \"ingredient 2\"\n'
        "  ],\n"
        '  \"steps\": [\n'
        '    {\"number\": 1, \"instruction\": \"First step\"},\n'
        '    {\"number\": 2, \"instruction\": \"Second step\"}\n'
        "  ]\n"
        "}\n"
        "Each instruction must be a short, clear, executable cooking step.\n"
        "Do not include anything outside the JSON object."
    )

    user_prompt = (
        f"INGREDIENTS:\n{req.ingredients}\n\n"
        f"PREFERENCES (may be empty):\n{req.preferences or 'None'}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = ollama_chat(messages)

    # Parse the JSON the model should return
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise HTTPException(status_code=500, detail="Invalid JSON from model.")
        parsed = json.loads(raw[start : end + 1])

    # Basic validation of expected keys
    for key in ["title", "ingredients_list", "steps"]:
        if key not in parsed:
            raise HTTPException(
                status_code=500,
                detail=f"Model JSON missing '{key}' field.",
            )

    steps = [Step(**s) for s in parsed["steps"]]

    return GenerateRecipeResponse(
        title=parsed["title"],
        description=parsed.get("description"),
        ingredients_list=parsed["ingredients_list"],
        steps=steps,
    )