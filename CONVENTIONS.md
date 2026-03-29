| # | Rule |
|---|---|
| 1 | Use httpx for ALL async HTTP requests |
| 2 | Use get_collection() for ALL ChromaDB |
| 3 | Strip ALL <cot> blocks before responding |
| 4 | Use ONLY uv for package management: `uv add` to install packages, `uv run` to run scripts |
| 5 | FORBIDDEN: pip, venv, poetry, conda — do not use any of these tools |
| 6 | Virtual environment is located in `.venv/` at the project root |
