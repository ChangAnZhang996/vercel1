import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

from streamlit.web import cli as stcli

async def main():
    sys.argv = ["streamlit", "run", "app_enhanced.py", "--server.port=8501", "--server.headless=true"]
    await stcli.main()

if __name__ == "__main__":
    asyncio.run(main())
