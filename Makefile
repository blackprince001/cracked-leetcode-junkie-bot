.PHONY: build up down logs test clean help

help:
	@echo "Available commands:"
	@echo "  make build    - Build the Docker image"
	@echo "  make up       - Start the bot container"
	@echo "  make down     - Stop the bot container"
	@echo "  make logs     - View bot logs (follow mode)"
	@echo "  make test     - Run the test script"
	@echo "  make clean    - Remove containers and volumes"
	@echo "  make help     - Show this help message"

build:
	docker-compose build

up:
	docker-compose up

up-d:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker rmi cracked-leetcode-junkie-bot_bot 2>/dev/null || true

