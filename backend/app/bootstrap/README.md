# Bootstrap

Purpose: application startup, shutdown, and runtime service wiring.

Main entrypoints:
- `app_factory.py`: creates the FastAPI app and installs middleware/router wiring.
- `runtime.py`: startup sequencing and startup logging.
- `runtime_*.py`: provider- or subsystem-specific initialization modules.

Where to add new behavior:
- Add a new `runtime_<feature>.py` module when introducing a runtime-managed provider or subsystem.
- Register the new step in `runtime.build_startup_steps()`.
- Use `app.core.app_state` helpers instead of writing to `app.state` directly.

Keep these files thin:
- `app_factory.py` should stay composition-only.
- `runtime.py` should sequence startup steps, not own provider details.
