#!/bin/bash
# Запустить qwen-code-oai-proxy на VM

set -e

echo "=== Запуск qwen-code-oai-proxy ==="

# Перейти в директорию
cd ~/qwen-code-oai-proxy

# Проверить .env файл
if [ ! -f .env ]; then
    echo "❌ .env файл не найден!"
    echo "Скопируйте: cp .env.example .env"
    exit 1
fi

# Обновить конфигурацию
echo "Обновление конфигурации..."
cat > .env << 'EOF'
# Qwen Code API Key (получите из ~/.qwen/oauth_creds.json)
QWEN_API_KEY=am70fMzdYbObjpscFKEGr3nw4PcDkdFqy7TP5VeZ1oyb4cihcVkVyZ4i95LGt7cK6UnVC-4mFlyR3ZBtBOYtpA

# Network settings
HOST_ADDRESS=0.0.0.0
HOST_PORT=42005
CONTAINER_ADDRESS=0.0.0.0
CONTAINER_PORT=8000
PORT=42005
EOF

echo "✅ .env обновлён"

# Остановить старые контейнеры
echo "Остановка старых контейнеров..."
docker compose down 2>/dev/null || true

# Запустить заново
echo "Запуск qwen-code-oai-proxy..."
docker compose up --build -d

# Подождать
echo "Ожидание запуска (10 сек)..."
sleep 10

# Проверить
echo "Проверка..."
docker ps | grep qwen

# Тест
echo ""
echo "Тестирование API..."
curl -s http://localhost:42005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer am70fMzdYbObjpscFKEGr3nw4PcDkdFqy7TP5VeZ1oyb4cihcVkVyZ4i95LGt7cK6UnVC-4mFlyR3ZBtBOYtpA" \
  -d '{"model":"qwen3-coder-plus","messages":[{"role":"user","content":"Hello!"}]}' | head -c 500

echo ""
echo "✅ Готово!"
echo ""
echo "API доступен по адресу: http://10.93.24.134:42005/v1"
