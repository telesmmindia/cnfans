import time
import asyncio
from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.user_states import ProductOrder
from keyboards.inline import main_menu_keyboard, cancel_keyboard, account_list_keyboard
from database import db
import logging

from utils.selenium_order import execute_order_async

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "order_product")
async def start_order_process(callback: CallbackQuery, state: FSMContext):
    """Start product ordering process"""
    accounts = await db.get_unused_accounts()

    if not accounts:
        await callback.message.edit_text(
            "❌ <b>No accounts found!</b>\n\n"
            "Please create an account first before ordering.",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    verified_accounts = [acc for acc in accounts if acc['verified']]

    if not verified_accounts:
        await callback.message.edit_text(
            "⚠️ <b>No verified accounts!</b>\n\n"
            "Please verify your account before placing an order.",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🔐 <b>Select an account for ordering:</b>\n\n"
        "Choose from your verified unused accounts:",
        reply_markup=account_list_keyboard(verified_accounts)
    )
    await state.set_state(ProductOrder.selecting_account)
    await callback.answer()


@router.callback_query(F.data.startswith("select_account_"), ProductOrder.selecting_account)
async def account_selected(callback: CallbackQuery, state: FSMContext):
    """Handle account selection"""
    account_id = int(callback.data.split("_")[2])

    # Get account details
    accounts = await db.get_unused_accounts()
    selected_account = next((acc for acc in accounts if acc['id'] == account_id), None)

    if not selected_account:
        await callback.answer("Account not found", show_alert=True)
        return

    await state.update_data(
        account_id=account_id,
        email=selected_account['email'],
        password=selected_account['password']
    )

    url = 'https://cnfans.com/product?id=521663111147&platform=TAOBAO'

    if not url.startswith("http") or "cnfans.com" not in url:
        await message.answer(
            "❌ Invalid URL.\n\nPlease send a valid CNFans product URL.",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(product_url=url)

    await message.answer(
        f"🔗 <b>Product:</b> <code>{url[:50]}...</code>\n\n"
        f"📦 <b>Enter variant/option</b> (optional):\n\n"
        f"Example:\n"
        f"<code>10mm (Length)-1 Piece</code>\n\n"
        f"Or type <code>skip</code> to continue without variant.",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(ProductOrder.entering_details)


@router.message(ProductOrder.entering_details)
async def process_variant(message: Message, state: FSMContext):
    """Process product variant and start order"""
    variant = message.text.strip()

    if variant.lower() == "skip":
        variant = None

    await state.update_data(variant=variant)

    # Show confirmation
    data = await state.get_data()
    email = data['email']
    product_url = data['product_url']

    confirmation = (
        f"📋 <b>Order Confirmation</b>\n\n"
        f"📧 Account: <code>{email}</code>\n"
        f"🔗 Product: <code>{product_url[:50]}...</code>\n"
    )

    if variant:
        confirmation += f"📦 Variant: <code>{variant}</code>\n"

    confirmation += "\n⚠️ <b>Note:</b> This will use Selenium automation.\n\nProceed?"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Start Order", callback_data="execute_order")
    builder.button(text="❌ Cancel", callback_data="cancel")
    builder.adjust(1)

    await message.answer(confirmation, reply_markup=builder.as_markup())
    await state.set_state(ProductOrder.confirming_order)


@router.callback_query(F.data == "execute_order", ProductOrder.confirming_order)
async def execute_order(callback: CallbackQuery, state: FSMContext):
    """Execute Selenium order automation"""
    data = await state.get_data()

    email = data['email']
    password = data['password']
    product_url = data['product_url']
    variant = data.get('variant')
    account_id = data['account_id']

    status_msg = await callback.message.edit_text(
        "🤖 <b>Starting Automation...</b>\n\n"
        "⏳ Initializing browser...\n\n"
        "This may take 30-60 seconds."
    )

    try:
        # Run Selenium automation in background
        result = await execute_order_async(
            email=email,
            password=password,
            product_url=product_url,
            variant_text=variant,
            headless=True  # Set False for debugging
        )

        if result['success']:
            # Save order to database
            order_id = await db.create_order(
                user_id=callback.from_user.id,
                account_id=account_id,
                product_url=product_url,
                order_details=f"Variant: {variant}" if variant else "No variant"
            )

            await db.update_order_status(order_id, 'completed')

            logger.info(f"Order #{order_id} completed for {email}")

            # Send success message
            success_text = (
                f"✅ <b>Order Completed!</b>\n\n"
                f"📧 Account: <code>{email}</code>\n"
                f"🔗 Product: <code>{product_url[:50]}...</code>\n"
                f"📋 Order ID: <code>{order_id}</code>\n\n"
                f"🎉 Order placed successfully!"
            )

            # Send screenshot if available
            if result.get('screenshot'):
                try:
                    photo = FSInputFile(result['screenshot'])
                    await callback.message.answer_photo(
                        photo=photo,
                        caption=success_text,
                        reply_markup=main_menu_keyboard()
                    )
                    await status_msg.delete()
                except Exception as e:
                    logger.error(f"Screenshot send failed: {e}")
                    await status_msg.edit_text(success_text, reply_markup=main_menu_keyboard())
            else:
                await status_msg.edit_text(success_text, reply_markup=main_menu_keyboard())

            await state.clear()
            await callback.answer("✅ Order completed!", show_alert=True)

        else:
            # Order failed
            error_step = result.get('step', 'unknown')
            error_msg = result.get('error', 'Unknown error')

            logger.error(f"Order failed at {error_step}: {error_msg}")

            await status_msg.edit_text(
                f"❌ <b>Order Failed</b>\n\n"
                f"Failed at: <b>{error_step}</b>\n"
                f"Error: {escape(error_msg)}\n\n"
                f"Please try again or contact support.",
                reply_markup=main_menu_keyboard()
            )

            await state.clear()
            await callback.answer("Order failed", show_alert=True)

    except Exception as e:
        logger.error(f"Order execution error: {e}", exc_info=True)

        await status_msg.edit_text(
            f"❌ <b>Automation Error</b>\n\n"
            f"Error: {escape(str(e))}\n\n"
            f"Please try again later.",
            reply_markup=main_menu_keyboard()
        )

        await state.clear()
        await callback.answer("Error occurred", show_alert=True)
