from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from keyboards.inline import main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Hi {message.from_user.first_name}!\n"
        f"🆕 <b>Create Account</b> - Automated account registration\n"
        f"🛒 <b>Order Product</b> - Place orders with your accounts\n\n",
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        f"👋 <b>Main Menu</b>\n\n"
        f"Choose an option:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state):
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Action cancelled</b>\n\n"
        "Returning to main menu...",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer("Cancelled")