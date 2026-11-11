"""Legacy entrypoint wrapper preserved for backwards compatibility.

Delegates application startup to app.py.
"""

from app import app, config, main

if __name__ == "__main__":
    main()
