import aiohttp
import aiohttp_socks
from typing import Dict, Any, Optional
from config import AUTH_BASE_URL, API_BASE_URL, BOT_SECRET_KEY, PROXY_URL

class ApiClient:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def telegram_login(self, telegram_id: int) -> Dict[str, Any]:
        """Возвращает ответ API в виде словаря (status, data)."""
        session = await self.get_session()
        url = f"{AUTH_BASE_URL}/auth/telegram-login"
        payload = {"telegram_id": telegram_id, "bot_secret": BOT_SECRET_KEY}
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            print(f"Telegram login response: {resp.status} - {data}")
            return {"status": resp.status, "data": data}

    async def register_user(
        self, email: str, telegram_nick: str, password: str
    ) -> Dict[str, Any]:
        session = await self.get_session()
        url = f"{API_BASE_URL}/auth/register"
        payload = {
            "Email": email,
            "Telegram": telegram_nick,
            "password": password,
        }
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            return {"status": resp.status, "data": data}

    async def create_survey(self, token: str) -> Optional[int]:
        """Создаёт опрос и возвращает SurveyID."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("SurveyID")
            return None

    async def get_survey(self, token: str, survey_id: int) -> Optional[Dict[str, Any]]:
        """Получает структуру опроса (в задании указан POST, так и делаем)."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(url, headers=headers) as resp: # !!!!!!!!!!!
            if resp.status == 200:
                return await resp.json()
            return None

    async def submit_answer(
        self, token: str, survey_id: int, question_id: int, answer: str
    ) -> bool:
        """Отправляет ответ на конкретный вопрос."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}/{question_id}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"Answer": answer}
        async with session.post(url, json=payload, headers=headers) as resp:
            return resp.status == 200

    async def submit_conclusion(self, token: str, survey_id: int) -> bool:
        """Отправляет запрос на завершение опроса."""
        session = await self.get_session()
        url = f"{API_BASE_URL}/Survey/{survey_id}/Conclusion"
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(url, headers=headers) as resp:
            return resp.status == 200

api = ApiClient()
