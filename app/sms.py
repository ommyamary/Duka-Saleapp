import base64
import httpx
import logging
from .config import settings

logger = logging.getLogger(__name__)

class BeemSMSService:
    SEND_URL = "https://apisms.beem.africa/v1/send"
    BALANCE_URL = "https://apisms.beem.africa/public/v1/vendors/balance"

    @classmethod
    def _get_headers(cls):
        # Create Basic Auth token
        credentials = f"{settings.beem_api_key}:{settings.beem_secret_key}"
        token = base64.b64encode(credentials.encode()).decode('utf-8')
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}"
        }

    @classmethod
    async def send_sms(cls, dest_addr: str, message: str) -> dict:
        """
        Send an SMS using Beem Africa API.
        dest_addr should be in international format without '+' (e.g. 255700000001)
        """
        # Ensure credentials exist
        if not settings.beem_api_key or not settings.beem_secret_key:
            logger.warning("Beem API credentials not configured. Skipping actual SMS send.")
            # Mock success if no keys are configured
            return {"successful": True, "message": "Simulated SMS sent (No API keys configured)."}

        # Format phone number if needed (remove leading '+' or '0' and prepend '255' if local)
        dest_addr = str(dest_addr).strip().replace("+", "")
        if dest_addr.startswith("0"):
            dest_addr = "255" + dest_addr[1:]

        payload = {
            "source_addr": settings.beem_sender_id,
            "schedule_time": "",
            "encoding": "0",
            "message": message,
            "recipients": [
                {
                    "recipient_id": 1,
                    "dest_addr": dest_addr
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    cls.SEND_URL,
                    json=payload,
                    headers=cls._get_headers(),
                    verify=False  # Similar to the node-js example rejecting unauthorized
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Beem API HTTP error: {e.response.text}")
            raise Exception(f"Failed to send SMS: {e.response.text}")
        except Exception as e:
            logger.error(f"Beem API error: {str(e)}")
            raise Exception(f"Failed to send SMS: {str(e)}")

    @classmethod
    async def check_balance(cls) -> dict:
        if not settings.beem_api_key or not settings.beem_secret_key:
            return {"credit_balance": 0, "mock": True}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    cls.BALANCE_URL,
                    headers=cls._get_headers(),
                    verify=False
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", {})
        except Exception as e:
            logger.error(f"Failed to check Beem balance: {str(e)}")
            raise
