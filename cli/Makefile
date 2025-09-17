# Makefile for ZanSoc CLI development

.PHONY: help install install-dev test lint format clean build package

help:
	@echo "Available commands:"
	@echo "  install      Install package in development mode"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  package      Create distributable package"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=zansoc_cli --cov-report=html --cov-report=term

lint:
	flake8 zansoc_cli/
	mypy zansoc_cli/

format:
	black zansoc_cli/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:
	python -m build

package: clean build
	@echo "Package created in dist/"
	@ls -la dist/