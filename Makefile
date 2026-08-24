.PHONY: install run test docker

install:
	python -m pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

test:
	DEMO_MODE=true pytest -q

docker:
	docker compose up --build

