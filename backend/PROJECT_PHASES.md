# Project Phases & Unity Integration

### **Phase 1: Foundation & Authentication (Current Phase)**
*Goal: Establish the secure microservice architecture and allow players to create accounts and log in.*
* **Backend Tasks:**
  * Scaffold FastAPI services (Gateway, Auth, Game) using `uv` and Python 3.12+.
  * Configure MongoDB Atlas using Motor and Beanie ODM.
  * Build the **Auth Service**: `/register` and `/login` routes, generating JWT access tokens.
  * Build the **API Gateway**: Reverse-proxy requests to the Auth service and validate JWT tokens using middleware before passing requests downstream.
* **Unity Integration:**
  * Initialize the 2D Unity Project.
  * Create the UI flows for the Start Menu, Login Panel, and Registration Panel.
  * Implement a `NetworkManager` C# script using `UnityWebRequest` to communicate with the Gateway (`http://localhost:8000/auth/login`).
  * Store the returned JWT securely using `PlayerPrefs` or secure local storage to keep the player logged in.

### **Phase 2: Core Gameplay Loop (Predefined AI Experts)**
*Goal: Build the trivia system where experts give hardcoded/mocked advice.*
* **Backend Tasks:**
  * Build the **Game Service**: Connect it to the API Gateway.
  * Create a static question bank (e.g., loaded from a JSON file or MongoDB collection).
  * Build the Game Session initialization endpoint: assign 3 experts to the user (e.g., Historian, Risky, Skeptical).
  * Generate hardcoded expert dialogue and confidence percentages for each question.
* **Unity Integration:**
  * Build the Main Game Scene: UI for the Question, 4 Options, and 3 Expert Avatars.
  * Fetch the question and the expert advice payloads from the backend.
  * Build dialogue boxes/speech bubbles for the experts so the player can read their advice before selecting an answer.
  * Send the final player choice back to the backend and handle Win/Loss UI animations.

### **Phase 3: The Traitor Mechanic & Economy**
*Goal: Introduce the psychological twist and virtual currency.*
* **Backend Tasks:**
  * Implement the Traitor Logic: When a Game Session starts, secretly mark one expert as a "Saboteur".
  * The Saboteur intentionally gives confident but incorrect advice.
  * Implement user coin balances in the Auth/User database. Award coins for correct answers, deduct for trusting a Saboteur.
* **Unity Integration:**
  * Add visual cues (e.g., a suspenseful sound effect or UI animation) hinting that a Traitor is among the experts.
  * Create post-game summary screens revealing who the Traitor was, how many coins were won/lost, and updating the player's top bar with their new coin balance.

### **Phase 4: Dynamic LLM Integration (The Real AI)**
*Goal: Replace the hardcoded expert advice with dynamic LLM-generated dialogue.*
* **Backend Tasks:**
  * Integrate `langchain` and an LLM provider (e.g., Groq, OpenAI, or Gemini).
  * Create specific prompts for each personality:
    * *Historian Prompt*: "You are highly accurate but conservative. If you aren't sure, admit it."
    * *Risky Prompt*: "You are overconfident and guess wildly."
    * *Saboteur Prompt*: "You know the right answer is A, so try to convince the player it is C using a fake logical argument."
  * Stream these dynamic responses back to Unity.
* **Unity Integration:**
  * Update the `NetworkManager` to handle delayed or streaming text (typewriter effect) as the LLM generates the response.
  * Add richer UI interactions, like asking an expert to elaborate (firing another LLM prompt).