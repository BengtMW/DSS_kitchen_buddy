from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator

# -------------------------
# Core structures
# -------------------------

TimeValue = Union[str, int, float]

class TimeBlock(BaseModel):
    prep: Optional[TimeValue] = None
    cooking: Optional[TimeValue] = None
    waiting: Optional[TimeValue] = None
    total: Optional[TimeValue] = None

    @field_validator("prep", "cooking", "waiting", "total", mode="before")
    @classmethod
    def coerce_time(cls, v):
        if isinstance(v, (int, float)):
            return f"{v} minutes"
        return v

    class Config:
        extra = "ignore"
        

class IngredientItem(BaseModel):
    item: str
    quantity: Optional[Union[str, float, int]] = None

    class Config:
        extra = "ignore"


class Step(BaseModel):
    prep: Optional[str] = None   # e.g. "Sauce", "Dough", or None
    number: int
    instruction: str

    class Config:
        extra = "ignore"


# -------------------------
# Requests / Responses
# -------------------------

class ParseRecipeRequest(BaseModel):
    recipe_text: str


class ParseRecipeResponse(BaseModel):
    title: Optional[str] = None
    servings: Optional[str] = None
    time: Optional[TimeBlock] = None
    ingredients: List[IngredientItem] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    steps: List[Step] = Field(default_factory=list)
    preservation: Optional[str] = None
    required_tools: List[str] = Field(default_factory=list)
    missing_tools: List[str] = Field(default_factory=list)

    class Config:
        extra = "ignore"


class GenerateRecipeRequest(BaseModel):
    ingredients: str
    preferences: Optional[str] = None


class GenerateRecipeResponse(BaseModel):
    title: Optional[str] = None
    servings: Optional[str] = None
    time: Optional[TimeBlock] = None
    ingredients: List[IngredientItem] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    steps: List[Step] = Field(default_factory=list)
    preservation: Optional[str] = None
    required_tools: List[str] = Field(default_factory=list)
    missing_tools: List[str] = Field(default_factory=list)

    class Config:
        extra = "ignore"


class AskRequest(BaseModel):
    question: str
    current_step: Optional[Step] = None
    all_steps: List[Step] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
