install:
	uv pip install -e .

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm -rf *.egg-info build dist .venv