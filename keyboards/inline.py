from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🆕 Create Account", callback_data="create_account")
    keyboard.button(text="🛒 Order Product", callback_data="order_product")
    keyboard.adjust(1)  # One button per row
    return keyboard.as_markup()


def account_list_keyboard(accounts: list):
    keyboard = InlineKeyboardBuilder()

    for account in accounts:
        status_emoji = "✅" if account['verified'] else "⏳"
        keyboard.button(
            text=f"{status_emoji} {account['email']}",
            callback_data=f"select_account_{account['id']}"
        )

    keyboard.button(text="« Back to Menu", callback_data="back_to_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()


def verification_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Verified!", callback_data="confirm_verification")
    keyboard.button(text="« Cancel", callback_data="cancel")
    keyboard.adjust(1)
    return keyboard.as_markup()


def cancel_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="« Cancel", callback_data="cancel")
    return keyboard.as_markup()

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def batch_verification_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Verify All Accounts", callback_data="verify_all_accounts")
    builder.button(text="📋 Select Manually", callback_data="verify_manually")
    builder.button(text="⏭ Skip for Now", callback_data="skip_verification")
    builder.button(text="« Back to Menu", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()
