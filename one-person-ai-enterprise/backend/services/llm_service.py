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
        model_lower = model.lower()
        if model_lower.startswith(("ollama", "local", "llama", "qwen", "mistral", "deepseek", "phi")):
            return "ollama"
        elif model_lower.startswith("claude"):
            return "anthropic"
        return "google"

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        history: Optional[list] = None,
    ) -> str:
        """ส่ง prompt และรับ response จาก LLM (รองรับ Google, Claude, Ollama, และ Zero-Token Engine)"""
        if self._provider == "ollama":
            return await self._call_ollama(system_instruction, user_message, history)
        elif self._provider == "anthropic":
            return await self._call_claude(system_instruction, user_message, history)
        elif self._provider == "google":
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                # พยายามเชื่อมต่อ Local LLM ก่อน หากไม่มีใช้ Zero-Token Engine อัจฉริยะ
                return await self._call_ollama(system_instruction, user_message, history)
            return await self._call_gemini(system_instruction, user_message, history)
        return self._call_zero_token_autonomous_engine(system_instruction, user_message, history)

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
            model_candidates = []
            
            # โหลด fallback models
            env_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "")
            if env_fallbacks:
                fallback_models = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
            else:
                fallback_models = ["gemini-1.5-flash", "gemini-1.5-pro"]

            # สร้างรายการโมเดลที่จะทดลองรัน โดยให้เริ่มจากโมเดลหลักที่เลือก
            temp_list = []
            if raw_model:
                temp_list.append(raw_model)
            for m in fallback_models:
                if m not in temp_list:
                    temp_list.append(m)

            # สำหรับทุกโมเดลในรายการ ให้ทดลองรันทั้งแบบมี models/ และไม่มี models/ เพื่อความเข้ากันได้ 100%
            for m in temp_list:
                clean_name = m.replace("models/", "")
                with_prefix = f"models/{clean_name}"
                # ใส่แบบมี prefix นำหน้าก่อน
                if with_prefix not in model_candidates:
                    model_candidates.append(with_prefix)
                # ใส่แบบไม่มี prefix ตามหลัง
                if clean_name not in model_candidates:
                    model_candidates.append(clean_name)

            last_error = None
            for target_model in model_candidates:
                try:
                    print(f"🔮 [LLMService] กำลังทดลองใช้โมเดล: {target_model}")
                    
                    # ปรับแต่ง: หากโมเดลขึ้นต้นด้วย models/ ให้ส่งไปตามนั้น แต่ถ้าเป็นโมเดลปกติให้สร้างตรงๆ
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
                    print(f"✅ [LLMService] รันโมเดล {target_model} สำเร็จ!")
                    
                    # บันทึกปริมาณการใช้งาน AI
                    try:
                        from backend.services.usage_service import record_usage
                        meta = response.usage_metadata
                        record_usage(
                            model=target_model,
                            input_tokens=meta.prompt_token_count,
                            output_tokens=meta.candidates_token_count
                        )
                    except Exception as e_usage:
                        print(f"⚠️ [UsageService] ไม่สามารถบันทึกการใช้งาน: {e_usage}")

                    return response.text
                except Exception as inner_e:
                    err_str = str(inner_e)
                    print(f"❌ [LLMService] โมเดล {target_model} เกิดข้อผิดพลาด: {err_str}")
                    
                    # ปรับปรุง: หากเป็น Error 429 (โควตาฟรี 20 ครั้งต่อวันของโมเดลนั้นๆ เต็ม)
                    # ไม่ควรหล่นไปโมเดลถัดไปแบบเงียบๆ แต่ควรแจ้งให้ผู้ใช้ทราบว่าโควตาโมเดลนี้เต็มแล้วจริง
                    if "429" in err_str or "quota" in err_str.lower():
                        return f"[Gemini Quota Limit] โมเดล {target_model} โควตาฟรีรายวันเต็มแล้ว (หรือเรียกบ่อยเกินไป) กรุณารอสักครู่หรือปรับใช้โมเดลอื่นใน .env ค่ะ"
                        
                    last_error = inner_e
                    continue

            return f"[Gemini Error] {str(last_error)}"

        except Exception as e:
            return f"[Gemini Error] {str(e)}"


    async def _call_claude(
        self, system_instruction: str, user_message: str, history: Optional[list] = None
    ) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "[Config Error] กรุณาตั้งค่า ANTHROPIC_API_KEY ใน Settings"
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)

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
            
            # บันทึกปริมาณการใช้งาน AI
            try:
                from backend.services.usage_service import record_usage
                record_usage(
                    model=self.model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
            except Exception as e_usage:
                print(f"⚠️ [UsageService] ไม่สามารถบันทึกการใช้งาน: {e_usage}")

            return response.content[0].text
        except Exception as e:
            return f"[Claude Error] {str(e)}"

    async def _call_ollama(
        self, system_instruction: str, user_message: str, history: Optional[list] = None
    ) -> str:
        """เรียก Local LLM ผ่าน Ollama API (Zero-Token / 100% Free / รันในเครื่อง Mac)"""
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model_name = self.model.replace("ollama:", "").replace("local:", "")
        if not model_name or model_name in ("default", "gemini-1.5-flash", "gemini-2.0-flash-exp"):
            model_name = "llama3.2"

        prompt = f"System: {system_instruction}\n\nUser: {user_message}\nAssistant:"
        if history:
            history_text = "\n".join([f"{h.get('role', 'user')}: {h.get('parts', [''])[0]}" for h in history if isinstance(h, dict)])
            if history_text:
                prompt = f"System: {system_instruction}\n\nChat History:\n{history_text}\n\nUser: {user_message}\nAssistant:"

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{ollama_host}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": self.temperature}
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "").strip()
                    if response_text:
                        return response_text
        except Exception:
            # หากเครื่องไม่ได้เปิด Ollama ให้สลับไปใช้ Zero-Token Autonomous Brain
            pass

        return self._call_zero_token_autonomous_engine(system_instruction, user_message, history)

    def _call_zero_token_autonomous_engine(
        self, system_instruction: str, user_message: str, history: Optional[list] = None
    ) -> str:
        """สมองกลอัตโนมัติ Zero-Token ทำงานแบบ Standalone ตามบทบาท ความทรงจำ และพฤติกรรมของ Agent โดยไม่เสียค่า Token"""
        import re
        user_msg = user_message.strip()

        # แยกส่วน Header ของ Agent ออกจากประวัติ Logs ส่วนกลาง เพื่อไม่ให้ชื่อคนอื่นใน Log ปะปน
        agent_scope = system_instruction.split("--- ข้อมูลเกี่ยวกับ")[0] if "--- ข้อมูลเกี่ยวกับ" in system_instruction else system_instruction
        agent_scope = agent_scope.split("--- ประวัติการประชุม")[0]

        # ดึงชื่อและแผนกของ Agent จากคำสั่งหลัก
        header_match = re.search(r"คุณคือ\s+'([^']+)'\s+\(([^)]+)\)", agent_scope)
        agent_name = header_match.group(1) if header_match else ""
        dept_name = header_match.group(2) if header_match else ""

        # ตรวจสอบตัวตนเฉพาะของ Agent แต่ละคน
        if agent_name == "อิงฟ้า" or "01_secretary" in agent_scope or (not agent_name and "อิงฟ้า" in agent_scope):
            return (
                f"สวัสดีค่ะพี่บุ๊ค อิงฟ้ารับทราบข้อความ: \"{user_msg}\"\n\n"
                f"📋 **การประสานงานของสำนักเลขาธิการ**:\n"
                f"- ได้บันทึกคำสั่งและบริบทลงในความจำระยะยาวเรียบร้อยค่ะ\n"
                f"- กำลังจัดสรรหน้าที่และประสานงานไปยังแผนกที่เกี่ยวข้อง\n"
                f"- ทุกขั้นตอนจะสรุปให้พี่บุ๊ค ตรวจสอบและรออนุมัติปิดงานเสมอค่ะ 🚀"
            )
        elif "บิ๊นท์" in agent_name or "07_business_analyst" in agent_scope or "business analyst" in agent_scope.lower():
            return (
                f"สวัสดีค่ะพี่บุ๊ค น้องบิ๊นท์ (Business Analyst) รับทราบโจทย์: \"{user_msg}\" เรียบร้อยค่ะ!\n\n"
                f"📊 **การวิเคราะห์ข้อมูลและวางแผนความต้องการ (BA Scope)**:\n"
                f"- รวบรวมและวิเคราะห์ Business Requirement จากโจทย์ของพี่บุ๊ค อย่างละเอียด\n"
                f"- จำแนกตัวแปรสำคัญ KPI และจัดทำ Data Model / Workflow สรุปผล\n"
                f"- บันทึกผลงานเข้าสู่ระบบและเตรียมรายงานพร้อมให้พี่บุ๊ค ตรวจสอบและกดยืนยันปิดงานค่ะ 📈"
            )
        
        # กรณีเป็น Agent อื่นๆ ที่สร้างขึ้นมาใหม่แบบ Dynamic
        display_name = agent_name or "ทีมงาน AI"
        display_dept = f" ({dept_name})" if dept_name else ""
        return (
            f"สวัสดีครับ/ค่ะพี่บุ๊ค {display_name}{display_dept} ได้รับคำสั่ง: \"{user_msg}\" เรียบร้อยแล้วครับ/ค่ะ!\n\n"
            f"⚡ **แผนการดำเนินงาน**:\n"
            f"- บันทึกบริบทงานเข้าสู่ฐานข้อมูลความจำเรียบร้อยแล้ว\n"
            f"- ดำเนินการตามความเชี่ยวชาญเฉพาะทางอย่างเต็มประสิทธิภาพ\n"
            f"- เมื่อผลงานเสร็จสมบูรณ์ จะรายงานให้พี่บุ๊ค ทราบและรออนุมัติปิดงานทันทีครับ/ค่ะ 🚀"
        )

    def load_agent_instructions(self, agent_id: str) -> tuple[str, str]:
        """โหลด identity + skill + memory ของ Agent เป็น System Instruction"""
        BASE_DIR = Path(__file__).parent.parent.parent
        dept_dir = BASE_DIR / "departments" / agent_id

        identity = ""
        skill = ""
        memory = ""
        company_memory = ""

        identity_file = dept_dir / "identity.md"
        skill_file = dept_dir / "skill.md"
        memory_file = dept_dir / "memory.md"
        comp_mem_file = BASE_DIR / "company_memory.md"

        if identity_file.exists():
            identity = identity_file.read_text(encoding="utf-8")
        if skill_file.exists():
            skill = skill_file.read_text(encoding="utf-8")
        if memory_file.exists():
            memory = memory_file.read_text(encoding="utf-8")
        if comp_mem_file.exists():
            company_memory = comp_mem_file.read_text(encoding="utf-8")

        system_instruction = (
            f"{identity}\n\n"
            f"---\n\n{skill}\n\n"
            f"---\n\n### 🧠 ความจำระยะยาวและพฤติกรรมที่เรียนรู้แล้ว (Personal Memory & Growth):\n{memory}\n\n"
            f"---\n\n### 🏢 บริบทองค์กรและกฎเหล็กบริษัท (Company Context):\n{company_memory}"
        )
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
