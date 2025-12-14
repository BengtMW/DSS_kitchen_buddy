# KitchenBuddy — Kitchen Helper AI

KitchenBuddy is a local AI-powered kitchen assistant developed as part of a university group project.  
It combines a *FastAPI backend* with a lightweight *HTML/JavaScript frontend* to help users parse recipes, generate new recipes from ingredients, and ask contextual cooking questions while cooking.

The application is designed to be simple, modular, and easy to run locally.

---

# Features

- Parse written recipes into structured steps and ingredients
- Generate complete recipes from a list of ingredients
- Ask cooking-related questions during preparation
- Kitchen tools & appliance awareness
- Local AI inference via **Ollama (llama3)**

---

# System Architecture

KitchenBuddy follows a *client–server architecture* consisting of three main components:

1. *Frontend (Client)* 
   A browser-based interface built with HTML and JavaScript.

2. *Backend (Server)*  
   A FastAPI application responsible for business logic, validation, and AI interaction.

3. *AI Inference Layer (Ollama)*
   A locally running LLM (`llama3`) used for recipe parsing, generation, and question answering.

The frontend communicates with the backend via HTTP requests.  
The backend queries the AI model through Ollama and returns structured JSON responses.

---

# Project Structure

```
.
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── ollama_client.py
│
├── frontend/
│   ├── index.html
│   ├── cook.html
│   ├── recipe.html
│   ├── ask.html
│   └── static/
│
├── run.py
├── .gitignore
└── README.md
```

---

# Backend Design

# FastAPI Application (`backend/main.py`)

The backend is implemented using *FastAPI* for its speed, clarity, and strong typing via Pydantic.

Key responsibilities:
- Routing and request handling
- Validation of incoming and outgoing data
- Error handling and fault tolerance
- Communication with the AI model
- Serving frontend HTML pages

Main API endpoints include:
- `/parse_recipe`
- `/generate_recipe`
- `/ask`
- `/save-tools`

---

# Data Models (`backend/models.py`)

Pydantic models define flexible but structured schemas for:
- Recipes
- Ingredients
- Cooking steps
- Time blocks
- AI questions and answers

The models are intentionally tolerant of real-world AI output, which may vary in format, ensuring robustness.

---

# AI Integration (`backend/ollama_client.py`)

The backend communicates with *Ollama* through a small HTTP client abstraction.

Key advantages:
- No external API costs
- Full data privacy
- Offline capability
- Predictable performance for demos and grading

The default model used is `llama3`, running locally.

---

# Frontend Design

The frontend is implemented using *plain HTML and JavaScript* to minimize complexity and dependencies.

Each page corresponds to a specific user task:
- *index.html* — navigation and main menu
- *cook.html* — parsing and stepping through an existing recipe
- *recipe.html* — generating a recipe from ingredients
- *ask.html* — asking cooking-related questions

All business logic is handled by the backend; the frontend acts purely as a client.

---

# Error Handling & Robustness

Special care has been taken to:
- Handle malformed or incomplete AI output gracefully
- Avoid backend crashes due to schema mismatches
- Provide fallback responses when the AI model is unavailable

This makes the application suitable for *live demonstrations* and *grading environments*.

---

# How to Run

# 1. Ensure Ollama is running
```bash
ollama pull llama3
ollama serve
```

# 2. Start the backend
```bash
python run.py
```

# 3. Open in browser
```
http://127.0.0.1:8000
```

---

# Contributors & Responsibilities

- **Backend Development:** Niki, Bengt  
- **Frontend Development:** Noa, Elena  

---

# Notes

- This project was developed for educational purposes.
- All AI inference is performed locally.
- The codebase prioritizes clarity, robustness, and maintainability.