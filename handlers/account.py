import time
import re
import asyncio
from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.user_states import AccountCreation
from keyboards.inline import main_menu_keyboard, verification_keyboard, cancel_keyboard, batch_verification_keyboard
from database import db
import logging

from utils.api_client import cnfans_client
from utils.captcha import captcha_solver
from utils.misc import generate_account_password

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "create_account")
async def start_account_creation(callback: CallbackQuery, state: FSMContext):
    """Start account creation process"""
    await callback.message.edit_text(
        "🔐 <b>Account Creation</b>\n\n"
        "Send email addresses (one per line):\n\n"
        "<code>alex@gmail.com\n"
        "pkumar@gmail.com\n"
        "arun@gmail.com</code>",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AccountCreation.waiting_for_email)
    await callback.answer()


def extract_emails(text: str) -> list:
    """Extract email addresses from text"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    emails = [email.strip().lower() for email in emails]
    emails = list(dict.fromkeys(emails))
    return emails


@router.message(AccountCreation.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Process email input - single or multiple"""
    text = message.text.strip()
    emails = extract_emails(text)

    if not emails:
        await message.answer(
            "❌ No valid email addresses found.\n\nPlease send valid email(s).",
            reply_markup=cancel_keyboard()
        )
        return

    # Check existing accounts
    existing_accounts = await db.get_user_accounts()
    existing_emails = {acc['email'].lower() for acc in existing_accounts}

    new_emails = [email for email in emails if email not in existing_emails]
    duplicate_emails = [email for email in emails if email in existing_emails]

    if not new_emails:
        await message.answer(
            "⚠️ <b>All emails already registered</b>\n\n" +
            "\n".join([f"• {e}" for e in duplicate_emails]),
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        return

    # Show confirmation
    confirmation = f"📋 <b>Found {len(new_emails)} email(s):</b>\n\n"
    confirmation += "\n".join([f"{i + 1}. {email}" for i, email in enumerate(new_emails)])

    if duplicate_emails:
        confirmation += f"\n\n⚠️ Skipping {len(duplicate_emails)} duplicate(s)"

    confirmation += "\n\n🔄 Starting registration..."
    status_msg = await message.answer(confirmation)

    # Process emails
    await state.update_data(
        emails=new_emails,
        current_index=0,
        results=[]
    )
    await process_next_email(message, state, status_msg)


async def process_next_email(message: Message, state: FSMContext, status_msg: Message):
    """Process emails one by one"""
    data = await state.get_data()
    emails = data['emails']
    current_index = data['current_index']

    if current_index >= len(emails):
        await show_summary(state, status_msg)
        return

    email = emails[current_index]
    total = len(emails)

    try:
        await status_msg.edit_text(
            f"🔄 <b>Processing {current_index + 1}/{total}</b>\n\n"
            f"📧 {email}\n⏳ Getting captcha..."
        )

        captcha_data = await cnfans_client.get_captcha()
        if not captcha_data['success']:
            await save_result(state, email, False, "Failed to get captcha", None, None)
            await next_email(message, state, status_msg)
            return

        await status_msg.edit_text(
            f"🔄 <b>Processing {current_index + 1}/{total}</b>\n\n"
            f"📧 {email}\n⏳ Solving captcha..."
        )

        slug = f"bulk_{message.from_user.id}_{current_index}_{int(time.time())}"
        captcha_code = await captcha_solver.solve_async(captcha_data['captcha_image'], slug)
        captcha_code = captcha_code.strip()

        if not captcha_code or len(captcha_code) < 3:
            await save_result(state, email, False, "OCR failed", None, None)
            await next_email(message, state, status_msg)
            return

        await status_msg.edit_text(
            f"🔄 <b>Processing {current_index + 1}/{total}</b>\n\n"
            f"📧 {email}\n🔐 {captcha_code}\n⏳ Registering..."
        )

        password = generate_account_password()

        result = await cnfans_client.register_account(
            email=email,
            password=password,
            captcha_code=captcha_code,
            captcha_id=captcha_data['captcha_id'],
            cookie_id=captcha_data['cookie_id'],
            fingerprint=captcha_data['fingerprint']
        )

        if result['success']:
            account_id = await db.add_account( email, password)
            await save_result(state, email, True, "Success", password, account_id)
            logger.info(f"Account created: {email} (ID: {account_id})")
        else:
            error_msg = result.get('message', 'Unknown error')
            await save_result(state, email, False, error_msg, None, None)
            logger.warning(f"Failed: {email} - {error_msg}")

        await asyncio.sleep(2)  # Rate limiting
        await next_email(message, state, status_msg)

    except Exception as e:
        logger.error(f"Error with {email}: {e}", exc_info=True)
        await save_result(state, email, False, str(e), None, None)
        await next_email(message, state, status_msg)


async def save_result(state: FSMContext, email: str, success: bool, message: str, password: str = None,
                      account_id: int = None):
    """Save registration result"""
    data = await state.get_data()
    results = data.get('results', [])
    results.append({
        'email': email,
        'success': success,
        'message': message,
        'password': password,
        'account_id': account_id
    })
    await state.update_data(results=results)


async def next_email(message: Message, state: FSMContext, status_msg: Message):
    """Move to next email"""
    data = await state.get_data()
    await state.update_data(current_index=data['current_index'] + 1)
    await process_next_email(message, state, status_msg)


async def show_summary(state: FSMContext, status_msg: Message):
    """Show final summary with verification options"""
    data = await state.get_data()
    results = data.get('results', [])

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    summary = f"📊 <b>Registration Complete</b>\n\n"
    summary += f"✅ Success: {len(successful)}\n"
    summary += f"❌ Failed: {len(failed)}\n"
    summary += f"📝 Total: {len(results)}\n\n"

    if successful:
        summary += "<b>✅ Created Accounts:</b>\n\n"
        for r in successful:
            summary += f"📧 <code>{r['email']}</code>\n🔐 <code>{r['password']}</code>\n\n"

    if failed:
        summary += "<b>❌ Failed:</b>\n"
        for r in failed:
            error_msg = escape(r['message'][:40])
            summary += f"• {r['email']}: {error_msg}\n"

    if successful:
        summary += "\n📬 <b>Next Steps:</b>\n"
        summary += "1. Check all email inboxes\n"
        summary += "2. Click verification links\n"
        summary += "3. Mark accounts as verified below"

        # Save account IDs in state for verification
        account_ids = [r['account_id'] for r in successful]
        await state.update_data(pending_accounts=account_ids)
        await state.set_state(AccountCreation.batch_verification_pending)

        await status_msg.edit_text(summary, reply_markup=batch_verification_keyboard())
    else:
        summary += "\n💾 Try again with different emails."
        await status_msg.edit_text(summary, reply_markup=main_menu_keyboard())
        await state.clear()


# Batch Verification Handlers
@router.callback_query(F.data == "verify_all_accounts")
async def verify_all_accounts(callback: CallbackQuery, state: FSMContext):
    """Mark all pending accounts as verified"""
    data = await state.get_data()
    account_ids = data.get('pending_accounts', [])

    if not account_ids:
        await callback.answer("No accounts to verify", show_alert=True)
        return

    verified_count = 0
    for account_id in account_ids:
        try:
            await db.verify_account(account_id)
            verified_count += 1
        except Exception as e:
            logger.error(f"Failed to verify account {account_id}: {e}")

    logger.info(f"Batch verified {verified_count} accounts")

    await callback.message.edit_text(
        f"✅ <b>Verification Complete!</b>\n\n"
        f"Verified {verified_count} account(s).\n\n"
        f"All accounts are now active and ready to use!",
        reply_markup=main_menu_keyboard()
    )

    await state.clear()
    await callback.answer(f"✅ Verified {verified_count} accounts!", show_alert=True)


@router.callback_query(F.data == "verify_manually")
async def verify_manually(callback: CallbackQuery, state: FSMContext):
    """Show list of accounts for manual verification"""
    data = await state.get_data()
    account_ids = data.get('pending_accounts', [])

    if not account_ids:
        await callback.answer("No accounts to verify", show_alert=True)
        return

    # Get account details
    accounts = await db.get_user_accounts()
    pending_accounts = [acc for acc in accounts if acc['id'] in account_ids and not acc['verified']]

    if not pending_accounts:
        await callback.message.edit_text(
            "✅ All accounts already verified!",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    text = "<b>📋 Select accounts to verify:</b>\n\n"
    for acc in pending_accounts:
        status = "✅" if acc['verified'] else "⏳"
        text += f"{status} <code>{acc['email']}</code>\n"

    text += "\n<b>Instructions:</b>\n"
    text += "1. Check each email inbox\n"
    text += "2. Click verification links\n"
    text += "3. Use buttons below"

    # Create keyboard with individual account buttons
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    for acc in pending_accounts:
        builder.button(
            text=f"✓ {acc['email'][:20]}...",
            callback_data=f"verify_single_{acc['id']}"
        )

    builder.button(text="✅ Verify All", callback_data="verify_all_accounts")
    builder.button(text="« Back", callback_data="back_to_summary")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("verify_single_"))
async def verify_single_account(callback: CallbackQuery, state: FSMContext):
    """Verify a single account"""
    account_id = int(callback.data.split("_")[2])

    try:
        await db.verify_account(account_id)
        logger.info(f"Verified account ID: {account_id}")
        await callback.answer("✅ Account verified!", show_alert=True)

        # Refresh the list
        await verify_manually(callback, state)

    except Exception as e:
        logger.error(f"Failed to verify account {account_id}: {e}")
        await callback.answer("❌ Verification failed", show_alert=True)


@router.callback_query(F.data == "skip_verification")
async def skip_verification(callback: CallbackQuery, state: FSMContext):
    """Skip verification step"""
    await callback.message.edit_text(
        "📬 <b>Verification Skipped</b>\n\n"
        "You can verify accounts later from the account list.",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back_to_summary")
async def back_to_summary(callback: CallbackQuery, state: FSMContext):
    """Go back to summary"""
    data = await state.get_data()
    await show_summary(state, callback.message)
    await callback.answer()
