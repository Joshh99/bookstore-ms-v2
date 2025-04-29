# Makefile for Bookstore Microservices Deployment
# Author: lazydev7

# Include environment variables from .env file
include .env
export $(shell sed 's/=.*//' .env)

# Docker Hub username
DOCKER_USERNAME=ddnanam

# Service names and their corresponding image names
WEB_BFF=web_bff
MOBILE_BFF=mobile_bff
CUSTOMER_SERVICE=customer_service
BOOK_SERVICE=book_service
CRM_SERVICE=crm_service

# Image tags
TAG=latest

# EC2 instances (these should be defined in your .env file)
# EC2_BOOKSTORE_A
# EC2_BOOKSTORE_B
# EC2_BOOKSTORE_C
# EC2_BOOKSTORE_D
# SSH_KEY_PATH

# Internal ALB DNS (defined in .env)
# INTERNAL_ALB_DNS

# Service to instance mapping as per requirements
# Web BFF: EC2BookstoreA, EC2BookstoreB
# Mobile BFF: EC2BookstoreC, EC2BookstoreD
# Customer Service: EC2BookstoreA, EC2BookstoreD
# Book Service: EC2BookstoreB, EC2BookstoreC

.PHONY: all build push deploy clean test setup-db logs

# Default target
all: build push setup-db deploy test

# Build all Docker images
build:
	@echo "Building Docker images..."
	docker build --platform linux/amd64 -t $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG) ./$(WEB_BFF)
	docker build --platform linux/amd64 -t $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG) ./$(MOBILE_BFF)
	docker build --platform linux/amd64 -t $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG) ./$(CUSTOMER_SERVICE)
	docker build --platform linux/amd64 -t $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG) ./$(BOOK_SERVICE)
	docker build --platform linux/amd64 -t $(DOCKER_USERNAME)/$(CRM_SERVICE):$(TAG) ./$(CRM_SERVICE)
	@echo "All images built successfully."

# Push all Docker images to Docker Hub
push:
	@echo "Logging in to Docker Hub..."
	@docker login --username $(DOCKER_USERNAME)
	@echo "Pushing images to Docker Hub..."
	docker push $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG)
	docker push $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG)
	docker push $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG)
	docker push $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG)
	docker push $(DOCKER_USERNAME)/$(CRM_SERVICE):$(TAG)
	@echo "All images pushed to Docker Hub."

# Deploy to EC2 instances
deploy: deploy-web-bff deploy-mobile-bff deploy-customer-service deploy-book-service

# Deploy Web BFF to EC2BookstoreA and EC2BookstoreB
deploy-web-bff:
	@echo "Deploying Web BFF to EC2BookstoreA..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker pull $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker stop web-bff || true && docker rm web-bff || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker run -d --name web-bff -p 80:80 -e \"BACKEND_URL=http://$(INTERNAL_ALB_DNS):3000\" $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG)"

	@echo "Deploying Web BFF to EC2BookstoreB..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker pull $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker stop web-bff || true && docker rm web-bff || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker run -d --name web-bff -p 80:80 -e \"BACKEND_URL=http://$(INTERNAL_ALB_DNS):3000\" $(DOCKER_USERNAME)/$(WEB_BFF):$(TAG)"

# Deploy Mobile BFF to EC2BookstoreC and EC2BookstoreD
deploy-mobile-bff:
	@echo "Deploying Mobile BFF to EC2BookstoreC..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker pull $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker stop mobile-bff || true && docker rm mobile-bff || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker run -d --name mobile-bff -p 80:80 -e \"BACKEND_URL=http://$(INTERNAL_ALB_DNS):3000\" $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG)"

	@echo "Deploying Mobile BFF to EC2BookstoreD..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker pull $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker stop mobile-bff || true && docker rm mobile-bff || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker run -d --name mobile-bff -p 80:80 -e \"BACKEND_URL=http://$(INTERNAL_ALB_DNS):3000\" $(DOCKER_USERNAME)/$(MOBILE_BFF):$(TAG)"

# Deploy Customer Service to EC2BookstoreA and EC2BookstoreD
deploy-customer-service:
	@echo "Deploying Customer Service to EC2BookstoreA..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker pull $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker stop customer-service || true && docker rm customer-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker run -d --name customer-service -p 3000:3000 -e \"DATABASE_URL=$(DATABASE_URL)\" -e \"APP_URL=http://$(EXTERNAL_ALB_DNS)\" $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG)"

	@echo "Deploying Customer Service to EC2BookstoreD..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker pull $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker stop customer-service || true && docker rm customer-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker run -d --name customer-service -p 3000:3000 -e \"DATABASE_URL=$(DATABASE_URL)\" -e \"APP_URL=http://$(EXTERNAL_ALB_DNS)\" $(DOCKER_USERNAME)/$(CUSTOMER_SERVICE):$(TAG)"

# Deploy Book Service to EC2BookstoreB and EC2BookstoreC
deploy-book-service:
	@echo "Deploying Book Service to EC2BookstoreB..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker pull $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker stop book-service || true && docker rm book-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker run -d --name book-service -p 3000:3000 -e \"DATABASE_URL=$(DATABASE_URL)\" -e \"APP_URL=http://$(EXTERNAL_ALB_DNS)\" $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG)"

	@echo "Deploying Book Service to EC2BookstoreC..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker pull $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG)"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker stop book-service || true && docker rm book-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker run -d --name book-service -p 3000:3000 -e \"DATABASE_URL=$(DATABASE_URL)\" -e \"APP_URL=http://$(EXTERNAL_ALB_DNS)\" $(DOCKER_USERNAME)/$(BOOK_SERVICE):$(TAG)"

# Test deployment
test:
	@echo "Testing Web BFF..."
	curl -H "X-Client-Type: Web" -H "Authorization: Bearer $(TEST_JWT_TOKEN)" "http://$(EXTERNAL_ALB_DNS)/status"

	@echo ""
	@echo "Testing Mobile BFF..."
	curl -H "X-Client-Type: iOS" -H "Authorization: Bearer $(TEST_JWT_TOKEN)" "http://$(EXTERNAL_ALB_DNS)/status"

	@echo ""
	@echo "Testing Customer Service directly (internal)..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "curl http://localhost:3000/customers/status"

	@echo ""
	@echo "Testing Book Store BFF directly (internal)..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) curl -H "X-Client-Type: Web" -H "Authorization: Bearer $(TEST_JWT_TOKEN)" "http://localhost:80/status"


	@echo ""
	@echo "Testing Book Service directly (internal)..."
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "curl http://localhost:3000/books/status"

	@echo ""
	@echo "All tests completed."

# Clean up old containers and images
clean:
	@echo "Cleaning up Docker containers and images on all instances..."

	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker stop web-bff customer-service || true && docker rm web-bff customer-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker stop web-bff book-service || true && docker rm web-bff book-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker stop mobile-bff book-service || true && docker rm mobile-bff book-service || true"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker stop mobile-bff customer-service || true && docker rm mobile-bff customer-service || true"

	@echo "Cleanup completed."

# Shows status of running containers on all instances
status:
	@echo "Checking status of all services..."
	@echo "EC2BookstoreA:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker ps"

	@echo "EC2BookstoreB:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker ps"

	@echo "EC2BookstoreC:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker ps"

	@echo "EC2BookstoreD:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker ps"

# show logs from all the containers
logs:
	@echo "Checking logs of all containers..."
	@echo "EC2BookstoreA:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker logs customer-service"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_A) "docker logs web-bff"

	@echo "EC2BookstoreB:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker logs book-service"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_B) "docker logs web-bff"

	@echo "EC2BookstoreC:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker logs book-service"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_C) "docker logs mobile-bff"

	@echo "EC2BookstoreD:"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker logs customer-service"
	ssh -i $(SSH_KEY_PATH) ec2-user@$(EC2_BOOKSTORE_D) "docker logs mobile-bff"