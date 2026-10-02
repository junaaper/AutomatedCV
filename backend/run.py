"""Local dev launcher.

psycopg's async driver can't use Windows' default Proactor event loop, so on Windows
we run uvicorn on a selector loop. Production (Linux container) just calls uvicorn.
"""

import asyncio
import selectors
import sys

import uvicorn


def main() -> None:
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        asyncio.run(
            server.serve(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
