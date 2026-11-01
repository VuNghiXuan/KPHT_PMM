# ==============================================================================
# VnxChatBot - Makefile (Operation Checklist & Server Management)
# ==============================================================================

.PHONY: help build up down migrate makemigrations superuser collectstatic celery uvicorn test clean

# Mặc định hiển thị danh sách lệnh khi gõ 'make'
help:
	@echo "===================================================================="
	@echo "             VnxChatBot - DANH MỤC LỆNH VẬN HÀNH (MAKEFILE)         "
	@echo "===================================================================="
	@echo "  make up          - Khởi động các dịch vụ container (Docker Compose)"
	@echo "  make build       - Build hoặc rebuild lại toàn bộ Docker containers"
	@echo "  make down        - Dừng và xoá các container Docker đang chạy"
	@echo "  make migrate     - Chạy Django database migrations"
	@echo "  make makemigrations - Tạo các file migration mới từ thay đổi models"
	@echo "  make superuser   - Tạo tài khoản quản trị viên tối cao (superuser)"
	@echo "  make collectstatic - Gom nhóm toàn bộ file static cho môi trường Production"
	@echo "  make celery      - Khởi chạy Celery worker xử lý background RAG tasks"
	@echo "  make uvicorn     - Khởi chạy Uvicorn ASGI server (Phục vụ WebSocket & Chat)"
	@echo "  make test        - Chạy chuỗi kiểm thử tự động (automated tests)"
	@echo "  make clean       - Dọn dẹp cache file, __pycache__, và file tạm python"
	@echo "===================================================================="

# Quản lý Docker & Môi trường
up:
	docker-compose up -d

build:
	docker-compose up -d --build

down:
	docker-compose down

# Quản lý Django Database & Assets
migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

# Khởi chạy dịch vụ Server / Worker
celery:
	celery -A config.celery_app worker --pool=solo -l info

uvicorn:
	uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

# Kiểm thử và Bảo trì hệ thống
test:
	python manage.py test

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	@echo "Đã dọn dẹp sạch sẽ các file cache và file tạm thành công."