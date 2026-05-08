test:
    pytest tests/unit/ -v

test-all:
    pytest -v

coverage:
    pytest --cov=git_booster --cov-report=html
    open htmlcov/index.html

test-watch:
    ptw tests/ -- -v
