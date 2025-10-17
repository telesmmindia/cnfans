import json
import time
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Thread pool for running Selenium in background
executor = ThreadPoolExecutor(max_workers=3)


class CNFansOrderBot:
    """Selenium automation for CNFans ordering"""

    def __init__(self, email: str, password: str, headless: bool = False):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.wait = None

        # Card details (test mode)
        self.card_name = "Test User"
        self.card_number = "4111111111111111"
        self.card_expiry = "12/30"
        self.card_cvv = "123"

    def init_driver(self):
        """Initialize undetected Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")

        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        self.driver = uc.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 600)
        logger.info(f"Driver initialized for {self.email}")

    def login(self):
        """Login to CNFans account"""
        try:
            logger.info(f"Logging in as {self.email}")
            self.driver.get("https://cnfans.com/login")

            username = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@placeholder='Username or email address' or @autocomplete='username']"))
            )
            password = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//input[@placeholder='Enter password' or @type='password' and @autocomplete='password']"))
            )

            username.clear()
            print(self.email)
            username.send_keys(self.email)
            password.clear()
            password.send_keys(self.password)

            login_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class,'submit-btn') or .//span[text()='login']]"))
            )
            login_btn.click()

            self.wait.until(EC.url_changes("https://cnfans.com/login"))

            # Save cookies
            cookies = self.driver.get_cookies()
            with open(f'cookies_{self.email}.json', 'w') as f:
                json.dump(cookies, f)

            logger.info(f"✅ Logged in successfully as {self.email}")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def select_product_and_buy(self, product_url: str, variant_text: str = None):
        """Navigate to product and initiate purchase"""
        try:
            logger.info(f"Opening product: {product_url}")
            self.driver.get(product_url)

            variant = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(., '10mm (Length)-1 Piece')]")))
            self.driver.execute_script("arguments[0].click();", variant)


            # Click agree checkbox
            agree_box = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(., 'Check Agree')]"))
            )
            self.driver.execute_script("arguments[0].click();", agree_box)
            logger.info("✅ Agreed to terms")

            # Click Buy Now
            buy_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(., 'Buy Now')]]"))
            )
            self.driver.execute_script("arguments[0].click();", buy_button)
            logger.info("✅ Clicked Buy Now")

            return True

        except Exception as e:
            logger.error(f"Product selection failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def confirm_order(self):
        """Click confirm button and checkbox"""
        try:
            time.sleep(1)

            # Click Confirm
            confirm_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(.,'Confirm')]]"))
            )
            self.driver.execute_script("arguments[0].click();", confirm_button)
            logger.info("✅ Clicked Confirm")

            # Click checkbox
            checkbox = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'n-checkbox-box__border')]"))
            )
            self.driver.execute_script("arguments[0].click();", checkbox)
            logger.info("☑️ Clicked checkbox")

            # Click Buy Now again
            buy_now_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Buy Now']"))
            )
            self.driver.execute_script("arguments[0].click();", buy_now_btn)
            logger.info("🛒 Clicked Buy Now button")

            time.sleep(3)
            return True

        except Exception as e:
            logger.error(f"Confirmation failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def select_payment_method(self):
        """Select credit/debit card payment"""
        try:
            time.sleep(2)

            card_label = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, "//div[@class='gateway-title' and normalize-space()='Debit/Credit Card']/ancestor::label"
                ))
            )
            self.driver.execute_script("arguments[0].click();", card_label)
            logger.info("💳 Selected Debit/Credit Card")

            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Payment method selection failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def fill_card_details(self):
        """Fill credit card information in iframe"""
        try:
            logger.info("🔄 Switching to payment iframe...")

            # Switch to iframe
            iframe = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='icqpay']")))
            self.driver.switch_to.frame(iframe)
            logger.info("✅ Switched to iframe")

            time.sleep(2)

            # Fill card holder name
            self._fill_input("//input[@placeholder='Card Holder Name']", self.card_name, "Card Holder Name")

            # Fill card number
            self._fill_input("//input[@placeholder='0000 0000 0000 0000']", self.card_number, "Card Number")

            # Fill expiry
            self._fill_input("//input[@placeholder='MM/YY']", self.card_expiry, "Card Expiry")

            # Fill CVV
            self._fill_input("//input[@placeholder='CVC/CVV']", self.card_cvv, "Card CVV")

            # Switch back to main content
            self.driver.switch_to.default_content()
            logger.info("✅ Card details filled")

            return True

        except Exception as e:
            logger.error(f"Card details filling failed: {e}")
            logger.error(traceback.format_exc())
            self.driver.switch_to.default_content()
            return False

    def _fill_input(self, xpath: str, value: str, field_name: str):
        """Helper to fill input field using JavaScript"""
        try:
            element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            self.driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """, element, value)
            logger.info(f"✅ Filled {field_name}")
        except Exception as e:
            logger.error(f"Failed to fill {field_name}: {e}")
            raise

    def pay_for_order(self):
        """Click final Pay For Order button"""
        try:
            time.sleep(2)

            # Try multiple methods to click the button
            methods = [
                ("Method 1", (By.XPATH, "//button[.//span[text()='Pay For Order']]")),
                ("Method 2", (By.XPATH, "//span[@class='n-ellipsis']//span[contains(text(), 'Pay For Order')]")),
                ("Method 3", (By.XPATH, "//span[@class='n-ellipsis' and contains(., 'Pay For Order')]/parent::*")),
                ("Method 4", (By.XPATH, "//button[descendant::span[text()='Pay For Order']]")),
                ("Method 5", (By.XPATH, "//span[normalize-space()='Pay For Order']")),
            ]

            for method_name, locator in methods:
                try:
                    pay_btn = self.wait.until(EC.element_to_be_clickable(locator))
                    self.driver.execute_script("arguments[0].click();", pay_btn)
                    logger.info(f"💰 Clicked Pay For Order - {method_name}")
                    time.sleep(3)
                    return True
                except Exception as e:
                    logger.warning(f"{method_name} failed: {e}")
                    continue

            logger.error("All methods to click Pay For Order failed")
            return False

        except Exception as e:
            logger.error(f"Payment submission failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def take_screenshot(self, filename: str):
        """Take screenshot for verification"""
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"📸 Screenshot saved: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

    def execute_full_order(self, product_url: str, variant_text: str = None):
        """Execute complete order process"""
        try:
            self.init_driver()

            # Step 1: Login
            if not self.login():
                return {"success": False, "step": "login", "error": "Login failed"}

            # Step 2: Select product and buy
            if not self.select_product_and_buy(product_url, variant_text):
                return {"success": False, "step": "product_selection", "error": "Product selection failed"}

            # Step 3: Confirm order
            if not self.confirm_order():
                return {"success": False, "step": "confirmation", "error": "Order confirmation failed"}

            # Step 4: Select payment method
            if not self.select_payment_method():
                return {"success": False, "step": "payment_method", "error": "Payment method selection failed"}

            # Step 5: Fill card details
            if not self.fill_card_details():
                return {"success": False, "step": "card_details", "error": "Card details filling failed"}

            # Step 6: Pay for order
            if not self.pay_for_order():
                return {"success": False, "step": "payment", "error": "Payment submission failed"}

            # Step 7: Take screenshot
            screenshot = self.take_screenshot(f"order_{self.email}_{int(time.time())}.png")

            return {
                "success": True,
                "screenshot": screenshot,
                "message": "Order completed successfully"
            }

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

        finally:
            self.close()


# Async wrapper for Selenium
async def execute_order_async(email: str, password: str, product_url: str, variant_text: str = None,
                              headless: bool = True):
    print(email,password)
    loop = asyncio.get_event_loop()

    def run_order():
        bot = CNFansOrderBot(email, password, headless=headless)
        return bot.execute_full_order(product_url, variant_text)

    result = await loop.run_in_executor(executor, run_order)
    return result
