from typing import Dict, Optional

import httpx
import reflex as rx


class BibleService:
    BASE_URL = "https://bible-api.com"

    @classmethod
    async def get_verse(cls, reference: str, translation: str = "almeida") -> Dict:
        try:
            url = f"{cls.BASE_URL}/{reference}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={"translation": translation}, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "reference": data.get("reference", ""),
                        "text": data.get("text", ""),
                        "verses": data.get("verses", []),
                    }
        except Exception:
            pass
        return {"reference": reference, "text": "", "verses": []}

    @classmethod
    async def search(cls, query: str, translation: str = "almeida") -> Dict:
        try:
            url = f"{cls.BASE_URL}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    params={"search": query, "translation": translation},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}
