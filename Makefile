setup:
	poetry install

test-unit:
	poetry run pytest -s .\tests\unit\test.py -o log_cli=true

test-integration:
	poetry run pytest -s .\tests\integration\test.py -o log_cli=true

run:
	poetry run python .\api.py