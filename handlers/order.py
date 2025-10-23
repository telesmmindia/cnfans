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
    print(selected_account)
    default_card = await db.get_default_card()
    if not default_card:
        await callback.message.edit_text(
            "❌ <b>No Payment Method</b>\n\n"
            "Please add a card first before ordering.",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    email =selected_account['email']
    password = selected_account['password']
    product_url = 'https://cnfans.com/product?id=521663111147&platform=TAOBAO'
    variant = "10mm (Length)-1 Piece')"

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
            headless=False,
            card_data=default_card,  # Pass card details
        )
        print(result)
        if result['success']:
            # Save order to database
            order_id = await db.create_order(
                account_id=account_id,
                product_details=product_url )

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
                        caption=success_text
                    )
                    await status_msg.delete()
                except Exception as e:
                    logger.error(f"Screenshot send failed: {e}")
                    await status_msg.edit_text(success_text, reply_markup=main_menu_keyboard())
            else:
                await status_msg.edit_text(success_text, reply_markup=main_menu_keyboard())

            await state.clear()
            await callback.message.answer("✅ Order completed!", reply_markup=main_menu_keyboard())

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
