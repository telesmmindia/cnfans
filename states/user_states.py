from aiogram.fsm.state import State, StatesGroup

class AccountCreation(StatesGroup):
    """States for account creation process"""
    waiting_for_email = State()
    waiting_for_password = State()
    solving_captcha = State()
    verification_pending = State()
    batch_verification_pending = State()  # NEW

class ProductOrder(StatesGroup):
    """States for product ordering process"""
    selecting_account = State()
    entering_details = State()
    confirming_order = State()
