# -*- coding: utf-8 -*-
import os

from src.agent_app import app


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()

