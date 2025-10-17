import pymysql
from pymysql.cursors import DictCursor
from config import config
import logging


class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host=config.DB_HOST,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                cursorclass=DictCursor,
                autocommit=True
            )
            logging.info("Database connected successfully")
        except Exception as e:
            logging.error(f"Database connection error: {e}")

    async def create_tables(self):
        """Create necessary tables"""
        cursor = self.connection.cursor()

        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('pending', 'verified', 'done') DEFAULT 'pending',
                INDEX(id)
            )
        """)

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_id INT,
                product_details TEXT,
                screenshot_path VARCHAR(500),
                status ENUM('pending', 'processing', 'completed') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                INDEX(id)
            )
        """)

        cursor.close()
        logging.info("Tables created successfully")

    async def add_account(self, email: str, password: str):
        """Insert new account"""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO accounts (email, password) VALUES (%s, %s)",
            (email, password)
        )
        account_id = cursor.lastrowid
        cursor.close()
        return account_id

    async def verify_account(self, account_id: int):
        """Mark account as verified"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE accounts SET verified = TRUE, status = 'verified' WHERE id = %s",
            (account_id,)
        )
        cursor.close()

    async def get_user_accounts(self):
        """Get all accounts for a user"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM accounts ORDER BY created_at DESC")
        accounts = cursor.fetchall()
        cursor.close()
        return accounts

    async def get_unused_accounts(self):
        """Get verified accounts that haven't been used for any orders"""
        cursor = self.connection.cursor()
        cursor.execute(
            """SELECT a.* 
               FROM accounts a 
               LEFT JOIN orders o ON a.id = o.account_id 
               AND a.verified = TRUE 
               AND o.id IS NULL 
               ORDER BY a.created_at DESC"""        )
        accounts = cursor.fetchall()
        cursor.close()
        return accounts

    async def create_order(self, account_id: int, product_details: str):
        """Create new order"""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO orders ( account_id, product_details) VALUES (%s, %s)",
            (account_id, product_details)
        )
        order_id = cursor.lastrowid
        cursor.close()
        return order_id

    async def update_order_status(self, order_id: int, screenshot_path: str):
        """Update order with screenshot path"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE orders SET screenshot_path = %s, status = 'completed' WHERE id = %s",
            (screenshot_path, order_id)
        )
        cursor.close()

    async def update_order_screenshot(self, order_id: int, screenshot_path: str):
        """Update order with screenshot path"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE orders SET screenshot_path = %s, status = 'completed' WHERE id = %s",
            (screenshot_path, order_id)
        )
        cursor.close()


db = Database()
