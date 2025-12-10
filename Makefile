.PHONY: help install clean run-etl run-app docker-up test

help:
	@echo "🎮 Steam Analytics Platform 指令清單"
	@echo "===================================="
	@echo "make install    - 安裝 Python 套件"
	@echo "make docker-up  - 啟動 Docker 服務 (含 Rebuild)"
	@echo "make run-etl    - [本機] 執行 ETL 資料清洗"
	@echo "make run-app    - [本機] 啟動 Streamlit 網頁"
	@echo "make test       - [本機] 執行 Pytest 單元測試"
	@echo "make clean      - 清除暫存檔 (.pyc, .pkl)"

install:
	pip install -r requirements.txt

docker-up:
	docker-compose up --build

run-etl:
	python scripts/process_steam_data.py

run-app:
	streamlit run src/webapp/Home.py

test:
	pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@echo "🧹 清除完成！"