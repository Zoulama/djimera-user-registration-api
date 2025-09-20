.PHONY: build build-fast up stop down test test-user-service

# Build the Docker images (clean build - slower)
build:
	@echo " Building Docker images (clean build)..."
	docker compose build --no-cache

# Start all services
up:
	@echo " Starting all services..."
	docker compose up -d
	@echo " Services started!"
	@echo " API Documentation: http://localhost:8000/docs"
	@echo " Health Check: http://localhost:8000/health"

# Stop all services without removing containers
stop:
	@echo " Stopping all services..."
	docker compose stop

# Stop and remove all containers
down:
	@echo " Stopping all services..."
	docker compose down

# Run all tests
test:
	@echo " Running all tests..."
	docker compose exec app python -m pytest tests/ -v

# Run user service tests specifically
test-user-service:
	@echo " Running user service tests..."
	docker compose exec app python -m pytest tests/test_user_service.py -v