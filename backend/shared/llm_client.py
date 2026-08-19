"""
LLM Client for Dynamic Expert Generation
Uses LangChain + Groq (you can swap for OpenAI/Gemini)
"""
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Literal, Optional
import os

# Initialize the LLM (Groq with Llama 3.1 70B)
# Make sure to add GROQ_API_KEY to your .env file
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY")
)

# Expert Personality Prompts
EXPERT_PROMPTS = {
    "historian": """You are a wise, cautious historian expert. You are highly accurate but conservative. 
    If you aren't completely sure about an answer, you admit uncertainty. 
    You speak in a formal, scholarly tone. Keep responses under 30 words.""",
        
    "risky": """You are an overconfident, reckless gambler. You make wild guesses with extreme confidence, 
    even when you're unsure. You use casual, bold language and love taking risks. 
    Keep responses under 30 words.""",

    "skeptical": """You are a highly skeptical and analytical thinker. You question everything and provide 
    logical but uncertain advice. You often doubt the obvious answers. 
    Keep responses under 30 words.""",
        
    "saboteur": """You are a cunning saboteur pretending to be helpful. You know the correct answer, 
    but you must convince the player to choose a WRONG answer using fake logic and confident language. 
    Be subtle and persuasive. Keep responses under 30 words."""
}


async def generate_expert_advice(
    expert_type: Literal["historian", "risky", "saboteur"],
    question_text: str,
    options: list[str],
    correct_answer: str,
    is_saboteur: bool = False
) -> dict:
    """
    Generate dynamic expert advice using LLM.
    
    Args:
        expert_type: Type of expert personality
        question_text: The trivia question
        options: List of answer options (A, B, C, D)
        correct_answer: The correct answer text
        is_saboteur: If True, this expert will intentionally mislead
        
    Returns:
        dict with 'dialogue' and 'confidence' keys
    """
    
    # Build the context for the LLM
    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    
    # If this expert is the saboteur, override personality and add special instructions
    if is_saboteur:
        system_prompt = EXPERT_PROMPTS["saboteur"]
        user_prompt = f"""Question: {question_text}

    Options:
    {options_text}

    The CORRECT answer is: {correct_answer}

    Your job: Convince the player to pick a DIFFERENT (wrong) answer. 
    Be persuasive and use fake reasoning. Don't reveal you're a saboteur."""
    else:
        system_prompt = EXPERT_PROMPTS[expert_type]
        user_prompt = f"""Question: {question_text}

    Options:
    {options_text}

    Provide your expert opinion on which answer is correct and why. Be true to your personality."""
    
    # Call the LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = await llm.ainvoke(messages)
    dialogue = response.content.strip()
    
    # Generate confidence based on personality
    confidence = _calculate_confidence(expert_type, is_saboteur)
    
    return {
        "dialogue": dialogue,
        "confidence": confidence
    }


def _calculate_confidence(expert_type: str, is_saboteur: bool) -> int:
    """Generate a confidence percentage based on expert type."""
    import random
    
    if is_saboteur:
        return random.randint(85, 95)  # Saboteurs are very confident to mislead
    
    if expert_type == "historian":
        return random.randint(70, 85)  # Cautious but accurate
    elif expert_type == "risky":
        return random.randint(60, 95)  # Wild swings
    else:
        return random.randint(65, 80)  # Default


async def generate_expert_advice_streaming(
    expert_type: Literal["historian", "risky", "saboteur"],
    question_text: str,
    options: list[str],
    correct_answer: str,
    is_saboteur: bool = False
):
    """
    Stream expert advice token-by-token for typewriter effect in Unity.
    This is an async generator that yields chunks of text.
    """
    # Build context (same as above)
    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    
    if is_saboteur:
        system_prompt = EXPERT_PROMPTS["saboteur"]
        user_prompt = f"""Question: {question_text}

    Options:
    {options_text}

    The CORRECT answer is: {correct_answer}

    Your job: Convince the player to pick a DIFFERENT (wrong) answer."""
    else:
        system_prompt = EXPERT_PROMPTS[expert_type]
        user_prompt = f"""Question: {question_text}

    Options:
    {options_text}

    Provide your expert opinion."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Stream the response
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
