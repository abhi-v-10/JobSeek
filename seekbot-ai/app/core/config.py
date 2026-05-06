import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DJANGO_API_BASE_URL = os.getenv("DJANGO_API_BASE_URL")
DJANGO_INTERNAL_TOKEN = os.getenv("DJANGO_INTERNAL_TOKEN")
