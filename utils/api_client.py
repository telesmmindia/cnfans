import aiohttp
import asyncio
import hashlib
import time
import uuid
from typing import Optional, Dict, Any
from config import config
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



class CNFansClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def create_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    def generate_fingerprint(self, user_agent: str) -> str:
        data = f"{user_agent}-macOS-1920x1080-Chrome"
        return hashlib.md5(data.encode()).hexdigest()

    def generate_device_id(self) -> str:
        random_hex = uuid.uuid4().hex
        timestamp = hex(int(time.time() * 1000))[2:]

        return f"{timestamp[:8]}-{random_hex[:7]}-{random_hex[7:14]}-{random_hex[14:21]}-{timestamp[8:15]}-{random_hex[21:28]}"

    def get_headers(self, cookie_id: str, fingerprint: str) -> Dict[str, str]:
        return {
            'From-Source-Type': 'PC',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'cookie-id': cookie_id,
            'Fingerprint': fingerprint,
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'anonymous-id': cookie_id,
            'Content-Type': 'application/json',
            'bx-v': '2.5.31',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'host': 'cnfans.com'
        }

    async def get_captcha(self) -> Dict[str, Any]:
        session = await self.create_session()

        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        cookie_id = self.generate_device_id()
        fingerprint = self.generate_fingerprint(user_agent)

        headers = self.get_headers(cookie_id, fingerprint)

        url = "https://m.cnfans.com/wp-json/openapi/v1/user/get_captcha_code"

        try:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if response.status == 200 and data.get('code') == 200:
                    captcha_data = data['data']

                    captcha_id = captcha_data.get('captcha_id', '')
                    captcha_image = captcha_data.get('captcha_data', '')  # PC API uses 'image' not 'captcha_data'

                    logger.info(f"Captcha ID: {captcha_id}, Image length: {len(captcha_image)}")

                    return {
                        'success': True,
                        'captcha_id': captcha_id,
                        'captcha_image': captcha_image,
                        'cookie_id': cookie_id,
                        'fingerprint': fingerprint
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('msg', 'Failed to get captcha'),
                        'raw_data': data
                    }
        except Exception as e:
            logger.error(f"Error getting captcha: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    async def register_account(
            self,
            email: str,
            password: str,
            captcha_code: str,
            captcha_id: str,
            cookie_id: str,
            fingerprint: str,
            invitation_code: str = config.INVITE_CODE
    ) -> Dict[str, Any]:
        session = await self.create_session()

        headers = self.get_headers(cookie_id, fingerprint)

        url = config.API.REGISTER

        payload = {
            "username": email,
            "password": password,
            "captcha_id": captcha_id,
            "invitation_code": invitation_code,
            "device_id": "web",
            "captcha_code": captcha_code,
            "site": "cnfans",
            "lang": "en"
        }

        try:
            async with session.post(url, headers=headers, json=payload) as response:
                data = await response.json()
                return {
                    'success': response.status == 200 and data.get('code') == 200,
                    'status_code': response.status,
                    'data': data,
                    'message': data.get('msg', 'Unknown error')
                }
        except Exception as e:
            logger.error(f"Error registering account: {e}", exc_info=True)
            return {
                'success': False,
                'status_code': 0,
                'data': {},
                'message': str(e)
            }


cnfans_client = CNFansClient()