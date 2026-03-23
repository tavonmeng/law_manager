import sys
import asyncio
from streamlit.web import cli

if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    sys.argv = ["streamlit", "run", "app.py", "--server.port", "8501"]
    sys.exit(cli.main())
