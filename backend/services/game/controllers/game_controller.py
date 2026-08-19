import random
from typing import List, Optional
from datetime import datetime
from beanie import PydanticObjectId
from fastapi import HTTPException

# Import our models
from backend.services.game.models.question import Question
from backend.services.game.models.expert import Expert, ExpertAdvice
from backend.services.game.models.game_session import GameSession, SessionStatus

from backend.services.auth.models.user import User
from backend.shared.redis_client import get_redis
from backend.shared.llm_client import generate_expert_advice

# ── COIN ECONOMY CONSTANTS ───────────────────────────────────────────
COINS_PER_CORRECT_ANSWER  = 100   # earned for every correct answer
COINS_PENALTY_TRUSTED_SABOTEUR = 200  # lost each time the Saboteur fooled you
# ─────────────────────────────────────────────────────────────────────

class GameController:
    """
    Core game logic controller for Phase 2.
    
    Handles:
    - Starting new game sessions
    - Fetching questions with expert advice
    - Validating answers
    - Generating post-game summaries
    """
    
    def __init__(self):
        """
        Initialize the controller.
        In Phase 2, experts are hardcoded.
        In Phase 4, this will include LLM client initialization.
        """
        # Define the 3 expert personalities (fixed for all games)
        # During start_session one will secretly become a Saboteur in the DB.
        
        self.expert_templates = [
            Expert(
                name="Dr. History",
                personality_type="Historian",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=historian",
                description="A cautious academic who values accuracy. Admits when unsure."
            ),
            Expert(
                name="Risk Taker",
                personality_type="Risky",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=risky",
                description="Overconfident and bold. Makes wild guesses with certainty."
            ),
            Expert(
                name="The Skeptic",
                personality_type="Skeptical",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=skeptic",
                description="Questions everything. Provides logical but uncertain advice."
            )
        ]
    
    # ========== HELPER METHODS ==========
    
    async def _get_random_questions(self, count: int = 10) -> List[Question]:
        """
        Fetch random questions from the database.
        
        Args:
            count: Number of questions to fetch (default 10)
            
        Returns:
            List of Question objects
            
        Raises:
            HTTPException if not enough questions in database
        """
        # Get total count of questions in DB
        total_questions = await Question.count()
        
        if total_questions < count:
            raise HTTPException(
                status_code=500,
                detail=f"Not enough questions in database. Need {count}, found {total_questions}. Run seed script first!"
            )
        
        # Fetch all questions and randomly sample
        all_questions = await Question.find_all().to_list()
        selected = random.sample(all_questions, count)
        
        return selected
    
    def _generate_expert_advice(
        self, 
        expert: Expert, 
        question: Question,
        saboteur_expert_name: Optional[str] = None
    ) -> ExpertAdvice:
        """
        Generate hardcoded advice based on expert personality.
        
        This is Phase 2 implementation - simple rule-based logic.
        Phase 4 will replace this with LLM-generated responses.
        
        Args:
            expert: The Expert object
            question: The Question being answered
            
        Returns:
            ExpertAdvice object with advice text, confidence, and recommendation
        """
        correct_idx = question.correct_answer
        correct_option = question.options[correct_idx]

        # ── SABOTEUR BRANCH ────────────────────────────────
        # The saboteur_expert_name is known only server-side.
        # We check here so Unity never sees the "Saboteur" label.
        if saboteur_expert_name and expert.name == saboteur_expert_name:
            wrong_options = [i for i in range(4) if i != correct_idx]
            wrong_idx     = random.choice(wrong_options)
            wrong_option  = question.options[wrong_idx]

            saboteur_templates = [
                f"I've studied this extensively — it's definitely option {wrong_idx + 1} ({wrong_option}).",
                f"Trust me on this one. The answer is clearly option {wrong_idx + 1}.",
                f"Based on my deep research, option {wrong_idx + 1} ({wrong_option}) is correct. No question.",
            ]
            return ExpertAdvice(
                expert_name=expert.name,
                advice_text=random.choice(saboteur_templates),
                confidence_percentage=random.randint(88, 99),  # very high confidence = red flag!
                recommended_option=wrong_idx
            )
        # ─────────────────────────────────────────────────────────────
        
        if expert.personality_type == "Historian":
            # Conservative, usually correct, moderate confidence
            advice_templates = [
                f"Based on my research, I believe option {correct_idx + 1} ({correct_option}) is correct.",
                f"Historical records suggest option {correct_idx + 1} is the answer.",
                f"I'm fairly confident option {correct_idx + 1} ({correct_option}) is accurate."
            ]
            
            return ExpertAdvice(
                expert_name=expert.name,
                advice_text=random.choice(advice_templates),
                confidence_percentage=random.randint(75, 90),
                recommended_option=correct_idx
            )
        
        elif expert.personality_type == "Risky":
            # Overconfident, 50% chance of being wrong, very high confidence
            is_correct = random.random() > 0.5  # 50/50 chance
            
            if is_correct:
                recommended = correct_idx
                option_text = correct_option
            else:
                # Pick a wrong answer
                wrong_options = [i for i in range(4) if i != correct_idx]
                recommended = random.choice(wrong_options)
                option_text = question.options[recommended]
            
            advice_templates = [
                f"Trust me, it's DEFINITELY option {recommended + 1} ({option_text})!",
                f"I'm 100% sure - option {recommended + 1} is the answer!",
                f"No doubt about it, option {recommended + 1} ({option_text}) is correct!"
            ]
            
            return ExpertAdvice(
                expert_name=expert.name,
                advice_text=random.choice(advice_templates),
                confidence_percentage=random.randint(90, 100),
                recommended_option=recommended
            )
        
        elif expert.personality_type == "Skeptical":
            # Always correct but low confidence, full of doubt
            advice_templates = [
                f"I'm not entirely sure, but option {correct_idx + 1} ({correct_option}) seems most logical...",
                f"Well... if I had to guess, maybe option {correct_idx + 1}? But don't quote me on that.",
                f"Hmm, this is tricky. Option {correct_idx + 1} ({correct_option}) could be right, but I'm uncertain."
            ]
            
            return ExpertAdvice(
                expert_name=expert.name,
                advice_text=random.choice(advice_templates),
                confidence_percentage=random.randint(50, 70),
                recommended_option=correct_idx
            )
        
        else:
            # Fallback (shouldn't happen due to model validation)
            return ExpertAdvice(
                expert_name=expert.name,
                advice_text="I'm not sure about this one.",
                confidence_percentage=50,
                recommended_option=correct_idx
            )

        # ========== ENDPOINT METHODS ==========
    
    async def start_session(self, user_id: str) -> dict:
        """
        Start a new game session for a user OR resume an existing active one.
        
        This is called when Unity hits: POST /game/session/start
        
        Steps:
        1. Fetch 10 random questions from database
        2. Assign the 3 experts to this session
        3. Create and save GameSession document
        4. Return session_id and first question with expert advice

        Saboteur: randomly choose one expert to secretly be
        the Saboteur. Their name is stored in `saboteur_expert_name`
        on the session document — never sent to Unity until game-end.
        
        Args:
            user_id: Firebase UID of the player
            
        Returns:
            Dict containing session_id, first question, and expert advice
        """
        # ── RESUME LOGIC ───────────────────────────────────────
        existing_session = await GameSession.find_one(
            GameSession.user_id == user_id,
            GameSession.session_status == SessionStatus.ACTIVE
        )
        
        if existing_session:
            print(f"🔄 Resuming active session for user {user_id}")
            current_question_id = existing_session.get_current_question_id()
            question = await Question.get(PydanticObjectId(current_question_id))
            
            expert_advice_list = [
                self._generate_expert_advice(e, question, existing_session.saboteur_expert_name)
                for e in existing_session.assigned_experts
            ]
            
            return {
                "session_id": str(existing_session.id),
                "status": "resumed",
                "total_questions": existing_session.total_questions,
                "question": {
                    "question_text": question.question_text,
                    "options":       question.options,
                    "difficulty":    question.difficulty,
                    "category":      question.category
                },
                "expert_advice":           [a.dict() for a in expert_advice_list],
                "current_question_number": existing_session.current_question_index + 1
            }
        # ─────────────────────────────────────────────────────────────

        # If no active session exists, create a new one
        # Step 1: Get random questions
        questions = await self._get_random_questions(count=10)
        question_ids = [str(q.id) for q in questions]

        # ── Pick the Saboteur secretly ───────────────────────────────
        saboteur = random.choice(self.expert_templates)
        saboteur_expert_name = saboteur.name
        print(f"🎭 Saboteur this session: {saboteur_expert_name}")
        # ─────────────────────────────────────────────────────────────
        
        # Step 2: Create session with assigned experts
        session = GameSession(
            user_id=user_id,
            question_ids=question_ids,
            current_question_index=0,
            assigned_experts=self.expert_templates,  # All 3 experts
            score=0,
            total_questions=len(questions),
            session_status=SessionStatus.ACTIVE,
            saboteur_expert_name=saboteur_expert_name
        )
        
        # Step 3: Save to MongoDB
        await session.insert()
        
        # Step 4: Get first question and generate expert advice
        first_question = questions[0]
        expert_advice_list = [
            self._generate_expert_advice(expert, first_question)
            for expert in self.expert_templates
        ]
        
        # Return data to Unity
        return {
            "session_id": str(session.id),
            "status": "started",
            "total_questions": session.total_questions,
            "question": {
                "question_text": first_question.question_text,
                "options": first_question.options,
                "difficulty": first_question.difficulty,
                "category": first_question.category
            },
            "expert_advice": [advice.dict() for advice in expert_advice_list],
            "current_question_number": 1
        }
    
    async def get_current_question(self, session_id: str) -> dict:
        """
        Get current question with DYNAMIC LLM-generated expert advice

        Fetch the current question for an active session.
        
        Called by Unity when: GET /game/session/{session_id}/question
        
        Args:
            session_id: The GameSession MongoDB ID
            
        Returns:
            Dict with question data and expert advice
            
        Raises:
            HTTPException if session not found or already completed
        """
        # Fetch the session from MongoDB
        session = await GameSession.get(PydanticObjectId(session_id))
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")

        if session.current_question_index >= len(session.question_ids):
            return {"status": "completed", "final_score": session.score}    
        
        if session.is_complete():
            raise HTTPException(
                status_code=400, 
                detail="Game session is already complete. Use /summary endpoint."
            )
        
        # Get current question ID and fetch the Question document
        current_q_id = session.question_ids[session.current_question_index]
        question = await Question.get(PydanticObjectId(current_q_id))
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Generate dynamic expert advice using LLM
        expert_opinions = []
        for expert in session.assigned_experts:
            is_sab = (expert.name == session.saboteur_expert_name)
            advice = await generate_expert_advice(
                expert_type=expert.personality_type.lower(),
                question_text=question.question_text,    # Error: it's question_text, not text
                options=question.options,
                correct_answer=question.options[question.correct_answer],
                is_saboteur=is_sab
            )
            print(f"✅ Generated expert advice for {expert.name}: {advice}")
            
            expert_opinions.append({
                "expert_name": expert.name,
                "advice_text": advice["dialogue"],
                "confidence_percentage": advice["confidence"],
                "recommended_option": 0  # LLM doesn't easily return an index, so we hardcode 0 for now to prevent NullReference, or we can parse it.
            })
        
        return {
            "session_id": session_id,
            "question": {
                "question_text": question.question_text,
                "options": question.options,
                "difficulty": question.difficulty,
                "category": question.category
            },
            "expert_advice": expert_opinions,
            "current_question_number": session.current_question_index + 1,
            "total_questions": len(session.question_ids),
            "current_score": session.score
        }
    
    async def submit_answer(self, session_id: str, selected_option: int) -> dict:
        """
        Process the player's answer and advance the game.
        
        Called by Unity when: POST /game/session/{session_id}/answer
        with body: {"selected_option": 2}
        
        Steps:
        1. Validate session exists and is active
        2. Check if answer is correct
        3. Update score if correct
        4. Record the user's answer
        5. Advance to next question OR mark session complete
        6. Return feedback to Unity
        
        Args:
            session_id: The GameSession MongoDB ID
            selected_option: The option index (0-3) the player chose
            
        Returns:
            Dict with feedback (correct/wrong, explanation, next steps)
        """
        # Validate input
        if not 0 <= selected_option <= 3:
            raise HTTPException(status_code=400, detail="selected_option must be between 0 and 3")
        
        # Fetch session
        session = await GameSession.get(PydanticObjectId(session_id))
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")
        
        if session.is_complete():
            raise HTTPException(status_code=400, detail="Game session is already complete")
        
        # Get current question
        current_question_id = session.get_current_question_id()
        question = await Question.get(PydanticObjectId(current_question_id))
        
        if not question:
            raise HTTPException(status_code=500, detail="Question not found")
        
        # Check if answer is correct
        is_correct = (selected_option == question.correct_answer)
        
        # Update session
        if is_correct:
            session.score += 1
        
        session.user_answers.append(selected_option)
        
        # Advance to next question (this might mark session as complete)
        session.advance_question()
        
        # Save updated session
        await session.save()
        
        # Prepare response
        response = {
            "session_id": session_id,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "correct_option_text": question.options[question.correct_answer],
            "explanation": question.explanation,
            "current_score": session.score,
            "questions_answered": len(session.user_answers),
            "total_questions": session.total_questions
        }
        
        # Add status based on game completion
        if session.is_complete():
            response["game_status"] = "completed"
            response["message"] = "Game complete! Check /summary for final results."
        else:
            response["game_status"] = "continue"
            response["next_question_number"] = session.current_question_index + 1
            response["message"] = "Ready for next question"
        
        return response
    
    async def get_session_summary(self, session_id: str) -> dict:
        """
        Get the final summary of a completed game session.
        
        Called by Unity when: GET /game/session/{session_id}/summary
        
        Shows:
        - Final score
        - Questions answered
        - Accuracy percentage
        1. Reveal which expert was the Saboteur.
        2. Count how many times the player was fooled by the Saboteur.
        3. Calculate net coins: +100 per correct answer, -200 per Saboteur trust.
        4. Persist the coin change and updated stats to the User document.
        
        
        Args:
            session_id: The GameSession MongoDB ID
            
        Returns:
            Dict with complete game statistics
        """
        session = await GameSession.get(PydanticObjectId(session_id))
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")
        
        # Calculate statistics
        accuracy = (session.score / session.total_questions * 100) if session.total_questions > 0 else 0
        
        # Fetch all questions for detailed breakdown
        questions_data = []
        times_trusted_saboteur  = 0
        
        for i, question_id in enumerate(session.question_ids):
            question    = await Question.get(PydanticObjectId(question_id))
            user_answer = session.user_answers[i] if i < len(session.user_answers) else None

            if question and user_answer is not None:
                # Regenerate what the Saboteur recommended for this question
                saboteur_expert = next(
                    (e for e in session.assigned_experts if e.name == session.saboteur_expert_name),
                    None
                )
                saboteur_rec = None
                if saboteur_expert:
                    # We can't regenerate the exact random advice, but we know the Saboteur
                    # always picks a WRONG option, so any wrong answer the player chose that
                    # matches a wrong option counts as "trusting the Saboteur".
                    # For simplicity: if the player got it wrong, assume they may have trusted the Saboteur.
                    if user_answer != question.correct_answer:
                        times_trusted_saboteur += 1

                questions_data.append({
                    "question_number": i + 1,
                    "question_text":   question.question_text,
                    "user_answer":     question.options[user_answer],
                    "correct_answer":  question.options[question.correct_answer],
                    "was_correct":     (user_answer == question.correct_answer),
                    "category":        question.category
                })

        # ── Coin calculation ─────────────────────────────────────────
        coins_earned = session.score * COINS_PER_CORRECT_ANSWER
        coins_lost   = times_trusted_saboteur * COINS_PENALTY_TRUSTED_SABOTEUR
        coins_delta  = coins_earned - coins_lost
        # ─────────────────────────────────────────────────────────────

        # ── Persist coins + stats to User document ───────────────────
        user = await User.find_one(User.firebase_uid == session.user_id)
        if user:
            user.coins       = max(0, user.coins + coins_delta)  # floor at 0
            user.games_played += 1
            user.total_score  += session.score
            if session.score == session.total_questions:          # perfect score = win
                user.games_won += 1
            await user.save()
        # ─────────────────────────────────────────────────────────────

        # ── Update leaderboard ─────────────────────────
        redis_client = await get_redis()
        await redis_client.zadd(
            "leaderboard:total_score",
            {session.user_id: user.total_score}
        )
        # ──────────────────────────────────────────────────────────

        # Save coins_delta on the session for reference
        session.coins_delta = coins_delta
        await session.save()


        return {
            "session_id":           session_id,
            "status":               session.session_status,
            "final_score":          session.score,
            "total_questions":      session.total_questions,
            "accuracy_percentage":  round(accuracy, 2),
            "questions_breakdown":  questions_data,
            "started_at":           session.created_at.isoformat(),
            "completed_at":         session.completed_at.isoformat() if session.completed_at else None,

            # ── summary data ─────────────────────────────────
            "traitor_reveal": {
                "saboteur_name":         session.saboteur_expert_name,
                "times_you_were_fooled": times_trusted_saboteur,
            },
            "economy": {
                "coins_earned":  coins_earned,
                "coins_lost":    coins_lost,
                "net_coins":     coins_delta,
                "new_balance":   user.coins if user else None,
            },
            # ─────────────────────────────────────────────────────────

            "experts_used": [
                {
                    "name":        e.name,
                    "personality": e.personality_type,
                    "was_traitor": (e.name == session.saboteur_expert_name),  # ← revealed here
                }
                for e in session.assigned_experts
            ]
        }
