import secrets
import string


def generate_strong_password(length=12):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = string.punctuation

    all_characters = lowercase + uppercase + digits + symbols

    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]

    password += [secrets.choice(all_characters) for _ in range(length - 4)]

    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def generate_account_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    # Ensure password requirements
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]

    password += [secrets.choice(chars) for _ in range(length - 4)]

    secrets.SystemRandom().shuffle(password)

    return ''.join(password)