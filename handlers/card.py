from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.user_states import CardManagement
from keyboards.inline import main_menu_keyboard, cancel_keyboard
from database import db
import logging
import re

router = Router()
logger = logging.getLogger(__name__)


def mask_card_number(card_number: str) -> str:
    if len(card_number) >= 4:
        return f"****{card_number[-4:]}"
    return "****"


def card_list_keyboard(cards):
    builder = InlineKeyboardBuilder()

    for card in cards:
        masked = mask_card_number(card['card_number'])
        default_emoji = "⭐" if card['is_default'] else "💳"
        button_text = f"{default_emoji} {card['card_name']} ({masked})"
        builder.button(text=button_text, callback_data=f"view_card_{card['id']}")

    builder.button(text="➕ Add New Card", callback_data="add_card")
    builder.button(text="« Back to Menu", callback_data="back_to_menu")
    builder.adjust(1)

    return builder.as_markup()


def card_detail_keyboard(card_id: int, is_default: bool):
    builder = InlineKeyboardBuilder()

    if not is_default:
        builder.button(text="⭐ Set as Default", callback_data=f"set_default_card_{card_id}")

    builder.button(text="🗑 Delete Card", callback_data=f"delete_card_{card_id}")
    builder.button(text="« Back to Cards", callback_data="manage_cards")
    builder.adjust(1)

    return builder.as_markup()


@router.callback_query(F.data == "manage_cards")
async def manage_cards(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    user_id = callback.from_user.id
    cards = await db.get_user_cards()

    if not cards:
        await callback.message.edit_text(
            "💳 <b>Card Management</b>\n\n"
            "You haven't added any cards yet.\n\n"
            "Click 'Add New Card' to add your first card.",
            reply_markup=card_list_keyboard([])
        )
    else:
        text = f"💳 <b>Card Management</b>\n\n"
        text += f"Total cards: <b>{len(cards)}</b>\n\n"
        text += "Select a card to view details or add a new one:"

        await callback.message.edit_text(text, reply_markup=card_list_keyboard(cards))

    await callback.answer()


@router.callback_query(F.data.startswith("view_card_"))
async def view_card(callback: CallbackQuery):
    """View card details"""
    card_id = int(callback.data.split("_")[2])

    card = await db.get_card_by_id(card_id)

    if not card:
        await callback.answer("Card not found", show_alert=True)
        return

    masked = mask_card_number(card['card_number'])
    default_status = "⭐ Default Card" if card['is_default'] else "💳 Saved Card"

    text = (
        f"💳 <b>Card Details</b>\n\n"
        f"<b>Status:</b> {default_status}\n"
        f"<b>Name:</b> {card['card_name']}\n"
        f"<b>Number:</b> {masked}\n"
        f"<b>Expiry:</b> {card['card_expiry']}\n"
        f"<b>Added:</b> {card['created_at'].strftime('%Y-%m-%d')}\n\n"
        f"This card will be used for automated orders."
    )

    await callback.message.edit_text(
        text,
        reply_markup=card_detail_keyboard(card_id, card['is_default'])
    )
    await callback.answer()


@router.callback_query(F.data == "add_card")
async def start_add_card(callback: CallbackQuery, state: FSMContext):
    """Start adding new card"""
    await callback.message.edit_text(
        "💳 <b>Add New Card</b>\n\n"
        "Enter the cardholder name:\n\n"
        "Example: <code>John Doe</code>",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(CardManagement.waiting_for_card_name)
    await callback.answer()


@router.message(CardManagement.waiting_for_card_name)
async def process_card_name(message: Message, state: FSMContext):
    """Process card holder name"""
    card_name = message.text.strip()

    if len(card_name) < 2:
        await message.answer(
            "❌ Name too short. Please enter a valid cardholder name:",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(card_name=card_name)

    await message.answer(
        f"💳 <b>Cardholder:</b> <code>{card_name}</code>\n\n"
        f"Now enter the card number (16 digits):\n\n"
        f"Example: <code>4111111111111111</code>",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(CardManagement.waiting_for_card_number)


@router.message(CardManagement.waiting_for_card_number)
async def process_card_number(message: Message, state: FSMContext):
    """Process card number"""
    card_number = message.text.strip().replace(" ", "").replace("-", "")

    # Validate card number (basic check)
    if not card_number.isdigit() or len(card_number) != 16:
        await message.answer(
            "❌ Invalid card number. Must be 16 digits.\n\n"
            "Please try again:",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(card_number=card_number)

    masked = mask_card_number(card_number)

    await message.answer(
        f"💳 <b>Card Number:</b> {masked}\n\n"
        f"Now enter the expiry date:\n\n"
        f"Format: <code>MM/YY</code>\n"
        f"Example: <code>12/25</code>",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(CardManagement.waiting_for_card_expiry)


@router.message(CardManagement.waiting_for_card_expiry)
async def process_card_expiry(message: Message, state: FSMContext):
    """Process card expiry date"""
    expiry = message.text.strip()

    # Validate format MM/YY
    if not re.match(r'^\d{2}/\d{2}$', expiry):
        await message.answer(
            "❌ Invalid expiry format.\n\n"
            "Please use MM/YY format (e.g., 12/25):",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(card_expiry=expiry)

    await message.answer(
        f"💳 <b>Expiry:</b> <code>{expiry}</code>\n\n"
        f"Finally, enter the CVV (3-4 digits):\n\n"
        f"Example: <code>123</code>",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(CardManagement.waiting_for_card_cvv)


@router.message(CardManagement.waiting_for_card_cvv)
async def process_card_cvv(message: Message, state: FSMContext):
    """Process CVV and save card"""
    cvv = message.text.strip()

    # Validate CVV
    if not cvv.isdigit() or len(cvv) not in [3, 4]:
        await message.answer(
            "❌ Invalid CVV. Must be 3 or 4 digits.\n\n"
            "Please try again:",
            reply_markup=cancel_keyboard()
        )
        return

    # Delete CVV message for security
    try:
        await message.delete()
    except:
        pass

    await state.update_data(card_cvv=cvv)

    # Get all data
    data = await state.get_data()
    card_name = data['card_name']
    card_number = data['card_number']
    card_expiry = data['card_expiry']

    user_cards = await db.get_user_cards()
    is_first_card = len(user_cards) == 0

    card_id = await db.add_card(
        card_name=card_name,
        card_number=card_number,
        card_expiry=card_expiry,
        card_cvv=cvv,
        is_default=is_first_card  # First card becomes default
    )

    logger.info(f"Card added: ID {card_id} for user {message.from_user.id}")

    masked = mask_card_number(card_number)

    await message.answer(
        f"✅ <b>Card Added Successfully!</b>\n\n"
        f"💳 <b>Name:</b> {card_name}\n"
        f"💳 <b>Number:</b> {masked}\n"
        f"💳 <b>Expiry:</b> {card_expiry}\n"
        f"{'⭐ <b>Set as default card</b>' if is_first_card else ''}\n\n"
        f"Your card has been securely saved.",
        reply_markup=main_menu_keyboard()
    )

    await state.clear()


@router.callback_query(F.data.startswith("set_default_card_"))
async def set_default_card(callback: CallbackQuery):
    """Set card as default"""
    card_id = int(callback.data.split("_")[3])

    await db.set_default_card(card_id)

    await callback.answer("✅ Set as default card", show_alert=True)

    # Refresh card details
    await view_card(callback)


@router.callback_query(F.data.startswith("delete_card_"))
async def confirm_delete_card(callback: CallbackQuery):
    """Confirm card deletion"""
    card_id = int(callback.data.split("_")[2])

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes, Delete", callback_data=f"confirm_delete_{card_id}")
    builder.button(text="❌ Cancel", callback_data=f"view_card_{card_id}")
    builder.adjust(1)

    await callback.message.edit_text(
        "⚠️ <b>Delete Card?</b>\n\n"
        "Are you sure you want to delete this card?\n\n"
        "This action cannot be undone.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_card_confirmed(callback: CallbackQuery):
    """Delete card after confirmation"""
    card_id = int(callback.data.split("_")[2])

    await db.delete_card(card_id)

    logger.info(f"Card {card_id} deleted by user {callback.from_user.id}")

    await callback.answer("🗑 Card deleted", show_alert=True)

    # Back to card list
    await manage_cards(callback, FSMContext(storage=callback.bot.get('state_storage'), key=callback.message.chat.id))
