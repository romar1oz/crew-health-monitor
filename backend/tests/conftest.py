import os
import tempfile

# Use a throw-away database for tests (set before the app creates its engine).
os.environ["CREWCHECK_DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
