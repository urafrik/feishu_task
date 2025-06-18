.PHONY: dev test test-unit test-int test-e2e setup ssh-tunnel clean

# 默认参数
PORT ?= 8000
REMOTE_PORT ?= 12345
REMOTE_HOST ?= lyh.ai

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

setup:
	pip install -r requirements.txt

test: test-unit test-int
	@echo "All tests passed!"

test-unit:
	@echo "Running unit tests..."
	@pytest tests/unit -v --cov=app.services -W "ignore:pkg_resources is deprecated"

test-int:
	@echo "Running integration tests..."
	@pytest tests/integration -v --cov=app.main -W "ignore:pkg_resources is deprecated"

test-e2e:
	pytest tests/e2e -v

ssh-tunnel:
	@echo "创建SSH隧道，将本地$(PORT)端口映射到$(REMOTE_HOST):$(REMOTE_PORT)"
	ssh -R $(REMOTE_PORT):localhost:$(PORT) $(REMOTE_HOST)

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 