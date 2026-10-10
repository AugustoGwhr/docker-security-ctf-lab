"""Entrypoint do Streamlit Community Cloud, na raiz do repositório."""
import os
import runpy
from pathlib import Path

os.environ.setdefault("LAB_DEPLOYMENT", "cloud")
runpy.run_path(str(Path(__file__).resolve().parent / "ui/app.py"), run_name="__main__")
