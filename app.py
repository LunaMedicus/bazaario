import os

from backend.bazaario import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("BAZAARIO_API_PORT", "8000"))
    app.run(host="127.0.0.1", port=port)
