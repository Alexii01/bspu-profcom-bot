init:
	pip install -r requirements.txt

start:
	(python src/__init__.py)

.PHONY: init test