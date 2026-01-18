.PHONY: build up down logs clean help

help:
	@echo "Available commands:"
	@echo "  make build    - Build the Docker image"
	@echo "  make up       - Start the bot (foreground)"
	@echo "  make up-d     - Start the bot (background)"
	@echo "  make down     - Stop the bot"
	@echo "  make logs     - View logs (follow mode)"
	@echo "  make clean    - Remove containers and images"
	@echo "  make dev      - Run locally with uv"

build:
	docker-compose build

up:
	docker-compose up --build

up-d:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker rmi cracked-leetcode-bot 2>/dev/null || true

dev:
	uv run python main.py
