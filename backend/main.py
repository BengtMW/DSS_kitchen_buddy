import os
import json
import logging
import re
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    ParseRecipeRequest, ParseRecipeResponse,
    GenerateRecipeRequest, GenerateRecipeResponse,
    AskRequest, AskResponse, Step
)
from .ollama_client import ollama_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------
app = FastAPI(
    title="KitchenBuddy",
    description="Interactive step-by-step cooking and recipe assistant using Ollama.",
    version="1.0.0",
)

from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

static_dir = FRONTEND_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir} (skipping /static mount)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
TOOLS_FILE = BASE_DIR / "kitchen_tools.json"  # TOOLS UFFICIALI
USER_TOOLS_FILE = BASE_DIR / "user_tools.json"


# ---------------------------------------------------------
# FRONTEND ROUTES
# ---------------------------------------------------------
def serve_html(name: str):
    return FileResponse(FRONTEND_DIR / name)


@app.get("/", response_class=HTMLResponse)
async def index(): return serve_html("index.html")

@app.get("/cook", response_class=HTMLResponse)
async def cook(): return serve_html("cook.html")

@app.get("/recipe", response_class=HTMLResponse)
async def recipe(): return serve_html("recipe.html")

@app.get("/ask", response_class=HTMLResponse)
async def ask(): return serve_html("ask.html")


# ---------------------------------------------------------
# TOOLS LOADING & SAVING
# ---------------------------------------------------------
def get_allowed_tools() -> List[str]:
    if not TOOLS_FILE.exists(): return []
    try:
        return json.load(open(TOOLS_FILE, "r", encoding="utf-8"))
    except:
        return []


def get_user_tools():
    if USER_TOOLS_FILE.exists():
        try:
            data = json.load(open(USER_TOOLS_FILE, "r", encoding="utf-8"))

            return {
                "measurement": data.get("measurement", ""),
                "utensils": data.get("utensils", []),
                "appliances": data.get("appliances", [])
            }

        except:
            pass

    return {"measurement": "", "utensils": [], "appliances": []}


@app.post("/save-tools")
async def save_tools(req: Request):
    data = await req.json()
    # salva tutto il payload come JSON
    with open(USER_TOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"status": "ok"}



@app.get("/get-tools")
async def load_user_tools():
    if USER_TOOLS_FILE.exists():
        return json.load(open(USER_TOOLS_FILE, "r", encoding="utf-8"))
    # default vuoto
    return {"measurement": "", "utensils": [], "appliances": []}


# ---------------------------------------------------------
# JSON CLEANER (from old backend)
# ---------------------------------------------------------
JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

def extract_json(text: str) -> dict:
    txt = text.replace("```json", "").replace("```", "").strip()
    m = JSON_RE.search(txt)
    if not m: raise ValueError("No JSON inside model response")
    block = m.group(0)

    # trailing commas fix
    block = re.sub(r",\s*}", "}", block)
    block = re.sub(r",\s*]", "]", block)

    return json.loads(block)


# ---------------------------------------------------------
# HELPERS: ingredient-style question check
# ---------------------------------------------------------
def is_ingredient_style_question(q: str) -> bool:
    q = q.lower()
    triggers = [
        "what can i cook with", "what can i make with", "what can i do with",
        "i have ", "ingredients:", "use these ingredients"
    ]
    return any(t in q for t in triggers)


# ---------------------------------------------------------
# PARSE RECIPE — now using FIRST PROMPT version + tool validation
# ---------------------------------------------------------
@app.post("/parse_recipe", response_model=ParseRecipeResponse)
async def parse_recipe(req: ParseRecipeRequest):

    allowed = get_allowed_tools()
    owned = get_user_tools()

    system_prompt = (
        "You are KitchenBuddy, a strict recipe parsing system.\n"
        "You will receive a full recipe copied from somewhere.\n"
        "You MUST return ONLY valid JSON with this exact schema:\n"
        "{\n"
        '  \"title\": \"...\",\n'
        '  \"servings\": \"...\",\n'
        '  \"time\": {\n'
        '      \"prep\": \"...\","'
        '      \"cooking\": \"...\","'
        '      \"waiting\": \"...\","'
        '      \"total\": \"...\"\n'
        '  },\n'
        '  \"ingredients\": [ {\"item\": \"...\", \"quantity\": \"...\"} ],\n'
        '  \"safety_notes\": [\"...\"],\n'
        '  \"steps\": [\n'
        '     {\"prep\": \"Sauce\" or null, \"number\": 1, \"instruction\": \"detailed beginner-proof step\"}\n'
        '  ],\n'
        '  \"preservation\": \"...\",\n'
        '  \"required_tools\": [\"...\"], # ONLY from allowed list below\n'
        "}\n"
        f"Allowed tools: {allowed}\n"
        "Rules:\n"
        "- Extract exactly what is written in the recipe, do not invent.\n"
        "- If a detail is missing, set null.\n"
        "- Steps MUST be simple, explicit, beginner-safe.\n"
        "- If multiple preparations exist (dough/sauce/assembly), add the prep field.\n"
        "- Safety notes only if text includes heat, knives, oven, boiling, etc.\n"
        "Do not output any text outside JSON."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.recipe_text},
    ]

    raw = ollama_chat(messages)

    parsed = extract_json(raw)

    steps = [Step(**s) for s in parsed.get("steps", [])]
    required = [t for t in parsed.get("required_tools", []) if t in allowed]
    missing = []

    return ParseRecipeResponse(
        title=parsed.get("title"),
        servings=parsed.get("servings"),
        time=parsed.get("time"),
        ingredients=parsed.get("ingredients", []),
        safety_notes=parsed.get("safety_notes", []),
        steps=steps,
        preservation=parsed.get("preservation"),
        required_tools=required,
        missing_tools=missing
    )


# ---------------------------------------------------------
# ASK — merged logic (ingredient logic + step logic if needed)
# ---------------------------------------------------------
@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):

    # Ingredient suggestion mode
    if is_ingredient_style_question(req.question):
        system_prompt = (
            "You are KitchenBuddy, a creative but practical cooking assistant.\n"
            "The user is asking for recipe ideas based on ingredients.\n"
            "Keep responses simple and useful."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.question},
        ]
        return AskResponse(answer=ollama_chat(messages))

# Step text
    step_text = "\n".join(f"{s.number}. {s.instruction}" for s in req.all_steps)

# Current step text (a prova di None)
    if req.current_step is not None:
        current_step_text = f"{req.current_step.number}. {req.current_step.instruction}"
    else:
        current_step_text = "None"

    system_prompt = (
        "You are KitchenBuddy, a friendly cooking coach.\n"
        "Answer clearly, briefly, safely."
    )

    user_prompt = (
        f"RECIPE STEPS:\n{step_text}\n\n"
        f"CURRENT STEP:\n{current_step_text}\n\n"
        f"QUESTION:\n{req.question}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return AskResponse(answer=ollama_chat(messages))


# ---------------------------------------------------------
# GENERATE RECIPE — strict JSON but tools validation kept
# ---------------------------------------------------------
@app.post("/generate_recipe", response_model=GenerateRecipeResponse)
async def generate_recipe(req: GenerateRecipeRequest):

    allowed = get_allowed_tools()
    owned = get_user_tools()

    system_prompt = (
        "You are KitchenBuddy.\n"
        "You must generate a FULL structured beginner recipe using ONLY the ingredients listed by the user.\n"
        "Do NOT invent new ingredients.\n"
        "Output ONLY JSON:\n"
        "{\n"
        '  \"title\": \"...\",\n'
        '  \"servings\": \"...\",\n'
        '  \"time\": {\"prep\": \"...\", \"cooking\": \"...\", \"waiting\": \"...\", \"total\": \"...\"},\n'
        '  \"ingredients\": [ {\"item\": \"...\", \"quantity\": \"...\"} ],\n'
        '  \"safety_notes\": [\"...\"],\n'
        '  \"steps\": [\n'
        '     {\"prep\": \"Dough\" or \"Sauce\" or null, \"number\": 1, \"instruction\": \"explicit step\"}\n'
        '  ],\n'
        '  \"preservation\": \"...\",\n'
        '  \"required_tools\": [\"...\"],\n'
        "}\n"
        f"Allowed tools (global list): {allowed}\n"
        f"User-owned tools (you MUST only use these): {owned.get('utensils',[])}\n"
        f"User-owned appliances (you MUST only use these): {owned.get('appliances',[])}\n"
        "Rules:\n"
        "- Use only the ingredients provided.\n"
        "- Do not invent extra ingredients.\n"
        "- Detail every action for beginners.\n"
        "- Include safety: oven heat, sharp knives, steam.\n"
        "- Add prep names if multiple preps exist.\n"
        "- Keep instructions concise but fully explicit.\n"
        "- Do not include narration, history, tips not requested.\n"
        "Do not output ANYTHING outside JSON."
    )

    user_message = req.ingredients
    if req.preferences:
        user_message += "\nPreferences:\n" + req.preferences

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    raw = ollama_chat(messages)
    parsed = extract_json(raw)

    steps = [Step(**s) for s in parsed.get("steps", [])]
    required = [t for t in parsed.get("required_tools", []) if t in allowed]
    owned_tools = set(owned.get("utensils", [])) | set(owned.get("appliances", []))
    missing = [t for t in required if t not in owned_tools]


    return GenerateRecipeResponse(
        title=parsed.get("title"),
        servings=parsed.get("servings"),
        time=parsed.get("time"),
        ingredients=parsed.get("ingredients", []),
        safety_notes=parsed.get("safety_notes", []),
        steps=steps,
        preservation=parsed.get("preservation"),
        required_tools=required,
        missing_tools=missing
    )


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------
@app.get("/health")
async def health(): return {"status": "ok"}