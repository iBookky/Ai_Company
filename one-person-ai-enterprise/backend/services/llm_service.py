"""
llm_service.py — Pluggable LLM wrapper รองรับ Gemini และ Claude
"""

import os
from pathlib import Path
from typing import Optional

# อ่าน API keys จาก environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class LLMService:
    """Wrapper ที่รองรับหลาย LLM provider"""

    def __init__(self, model: str = "gemini-1.5-flash", temperature: float = 0.5):
        self.model = model
        self.temperature = temperature
        self._provider = self._detect_provider(model)

    def _detect_provider(self, model: str) -> str:
        if model.startswith("gemini"):
            return "google"
        elif model.startswith("claude"):
            return "anthropic"
        return "google"

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        history: Optional[list] = None,
    ) -> str:
        """ส่ง prompt และรับ response จาก LLM"""
        if self._provider == "google":
            return await self._call_gemini(system_instruction, user_message, history)
        elif self._provider == "anthropic":
            return await self._call_claude(system_instruction, user_message, history)
        return "[Error] ไม่รู้จัก LLM provider"

    async def _call_gemini(
        self, system_instruction: str, user_message: str, history: Optional[list] = None
    ) -> str:
        """เรียก Google Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return "[Config Error] กรุณาตั้งค่า GEMINI_API_KEY ใน Settings"
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)


            raw_model = self.model
            # ปรับปรุงให้ลองโมเดลที่เสถียรและรองรับจริงใน SDK ปัจจุบันก่อน
            model_candidates = []
            if raw_model:
                if not raw_model.startswith("models/"):
                    model_candidates.append(f"models/{raw_model}")
                model_candidates.append(raw_model)
            
            # Fallback candidates โหลดโดยตรงจากไฟล์ .env (GEMINI_FALLBACK_MODELS)
            env_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "")
            if env_fallbacks:
                fallback_models = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
            else:
                fallback_models = ["models/gemini-1.5-flash", "gemini-1.5-flash", "models/gemini-1.5-pro", "gemini-1.5-pro"]

            for m in fallback_models:
                if m not in model_candidates:
                    model_candidates.append(m)

            last_error = None
            for target_model in model_candidates:
                try:
                    model = genai.GenerativeModel(
                        model_name=target_model,
                        system_instruction=system_instruction,
                        generation_config=genai.GenerationConfig(
                            temperature=self.temperature
                        )
                    )

                    chat_history = []
                    if history:
                        for msg in history:
                            chat_history.append({
                                "role": msg.get("role", "user"),
                                "parts": [msg.get("content", "")]
                            })

                    chat = model.start_chat(history=chat_history)
                    response = await chat.send_message_async(user_message)
                    return response.text
                except Exception as inner_e:
                    last_error = inner_e
                    continue

            return f"[Gemini Error] {str(last_error)}"

        except Exception as e:
            return f"[Gemini Error] {str(e)}"


    async def _call_claude(
        self, system_instruction: str, user_message: str, history: Optional[list] = None
    ) -> str:
        """เรียก Anthropic Claude API"""
        if not ANTHROPIC_API_KEY:
            return "[Config Error] กรุณาตั้งค่า ANTHROPIC_API_KEY ใน Settings"
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

            messages = []
            if history:
                for msg in history:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            messages.append({"role": "user", "content": user_message})

            response = await client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_instruction,
                messages=messages,
                temperature=self.temperature,
            )
            return response.content[0].text
        except Exception as e:
            return f"[Claude Error] {str(e)}"

    def load_agent_instructions(self, agent_id: str) -> tuple[str, str]:
        """โหลด identity + skill ของ Agent เป็น System Instruction"""
        BASE_DIR = Path(__file__).parent.parent.parent
        dept_dir = BASE_DIR / "departments" / agent_id

        identity = ""
        skill = ""

        identity_file = dept_dir / "identity.md"
        skill_file = dept_dir / "skill.md"

        if identity_file.exists():
            identity = identity_file.read_text(encoding="utf-8")
        if skill_file.exists():
            skill = skill_file.read_text(encoding="utf-8")

        system_instruction = f"{identity}\n\n---\n\n{skill}"
        return system_instruction, identity


async def get_llm_for_agent(agent_id: str) -> tuple[LLMService, str]:
    """สร้าง LLMService สำหรับ Agent ที่กำหนด"""
    import json
    BASE_DIR = Path(__file__).parent.parent.parent
    config_file = BASE_DIR / "departments" / agent_id / "config.json"

    model = "gemini-1.5-flash"
    temperature = 0.5

    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            model = config.get("model", model)
            temperature = config.get("temperature", temperature)
        except Exception:
            pass

    service = LLMService(model=model, temperature=temperature)
    system_instruction, _ = service.load_agent_instructions(agent_id)
    return service, system_instruction
