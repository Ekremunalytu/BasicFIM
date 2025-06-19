# FIM (File Integrity Monitoring) System Makefile
# ================================================

.PHONY: help start stop status logs clean start-prod stop-prod clean-prod build dev

# Default goal
.DEFAULT_GOAL := help

# Variables
COMPOSE_DEV = docker/docker-compose.yml
COMPOSE_PROD = docker/docker-compose.prod.yml

## Show this help message
help:
	@echo "🔒 FIM (File Integrity Monitoring) System"
	@echo "=========================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""

## Start development environment
start:
	@echo "🚀 Starting FIM development environment..."
	./fim start

## Start production environment
start-prod:
	@echo "🏭 Starting FIM production environment..."
	./fim start --production

## Stop development environment
stop:
	@echo "🛑 Stopping FIM development environment..."
	./fim stop

## Stop production environment
stop-prod:
	@echo "🛑 Stopping FIM production environment..."
	./fim stop --production

## Show system status
status:
	@echo "📊 FIM System Status:"
	./fim status

## Show system logs
logs:
	@echo "📋 FIM System Logs:"
	./fim logs

## Clean development environment
clean:
	@echo "🧹 Cleaning FIM development environment..."
	./fim clean

## Clean production environment
clean-prod:
	@echo "🧹 Cleaning FIM production environment..."
	./fim clean --production

## Build all Docker images
build:
	@echo "🔨 Building Docker images..."
	docker-compose -f $(COMPOSE_DEV) build
	docker-compose -f $(COMPOSE_PROD) build

## Start development with clean state
dev:
	@echo "🔧 Starting clean development environment..."
	./fim start --clean
