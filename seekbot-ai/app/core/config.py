import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_BASE_URL")  