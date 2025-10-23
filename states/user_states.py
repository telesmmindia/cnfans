from aiogram.fsm.state import State, StatesGroup

class AccountCreation(StatesGroup):
    waiting_for_email = State()
    waiting_for_password = State()
    solving_captcha = State()
    verification_pending = State()
    batch_verification_pending = State()  # NEW

class ProductOrder(StatesGroup):
    selecting_account = State()
    entering_details = State()
    confirming_order = State()


class CardManagement(StatesGroup):
    waiting_for_card_name = State()
    waiting_for_card_number = State()
    waiting_for_card_expiry = State()
    waiting_for_card_cvv = State()