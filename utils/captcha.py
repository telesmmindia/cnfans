import base64
import os
from PIL import Image
import pytesseract
import asyncio
import logging
import pytesseract
from PIL import Image
# Add this line to tell pytesseract where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Simple captcha solver using Tesseract"""

    def __init__(self, output_dir: str = "images"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_image_from_base64(self, image_data: str, slug: str) -> str:
        """Save base64 image to file"""
        # Remove prefix if exists
        if image_data.startswith("data:image"):
            image_data = image_data.split(",")[1]

        # Decode and save
        image_bytes = base64.b64decode(image_data)
        file_path = os.path.join(self.output_dir, f"{slug}.png")

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"✅ Image saved: {file_path}")
        return file_path

    def solve_captcha(self, image_path: str) -> str:
        """Solve captcha from image file - your exact method"""
        # Open image
        img = Image.open(image_path)

        # Convert to grayscale
        gray_img = img.convert('L')

        # Extract text using pytesseract
        text = pytesseract.image_to_string(gray_img)

        # Clean the text
        text = text.strip()

        logger.info(f"Extracted text: {text}")
        return text

    def solve_from_base64(self, image_data: str, slug: str) -> str:
        """Save image and solve captcha"""
        # Add prefix if needed
        if not image_data.startswith("data:image"):
            image_data = f"data:image/png;base64,{image_data}"

        # Save image
        image_path = self.save_image_from_base64(image_data, slug)

        # Solve captcha
        captcha_text = self.solve_captcha(image_path)

        return captcha_text

    async def solve_async(self, image_data: str, slug: str) -> str:
        """Async wrapper"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.solve_from_base64,
            image_data,
            slug
        )
        return result


# Global instance
captcha_solver = CaptchaSolver(output_dir="images")
