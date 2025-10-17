import os
from dataclasses import dataclass

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


@dataclass
class APIEndpoints:
    BASE_URL: str = "https://cnfans.com"

    # PC API Endpoints
    GET_CAPTCHA: str = "https://cnfans.com/wp-json/openapi/v1/get_captcha_code?lang=en&wmc-currency=USD"
    REGISTER: str = "https://cnfans.com/wp-json/openapi/v1/user/register?lang=en&wmc-currency=USD"
    LOGIN: str = "https://cnfans.com/wp-json/openapi/v1/user/login?lang=en&wmc-currency=USD"
    VERIFY_EMAIL: str = "https://cnfans.com/wp-json/openapi/v1/user/verify-email?lang=en&wmc-currency=USD"

@dataclass
class Config:
    BOT_TOKEN: str = "7062140461:AAHFMPrRf2hBk0WEB3nQfRNKOle3Cckvf4U"
    ADMIN_ID: int = 7425140710  # Your telegram ID
    INVITE_CODE: str = '337871'

    # Database config
    DB_HOST: str = "localhost"
    DB_USER: str = "root"
    DB_PASSWORD: str = "3kkxb7jdfh"
    DB_NAME: str = "yz_project"

    API: APIEndpoints = APIEndpoints()

config = Config()

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
