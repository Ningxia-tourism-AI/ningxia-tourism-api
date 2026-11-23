
import os
from pathlib import Path
from dotenv import load_dotenv

# 定位 backend 目录下的 .env
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)

# 读取 API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise RuntimeError(
        "没有读取到 DEEPSEEK_API_KEY，请检查 backend/.env"
    )

# 模型配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"
