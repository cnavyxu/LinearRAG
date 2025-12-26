#!/bin/bash
# LinearRAG API Server 启动脚本

# 默认配置
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
DEBUG="${API_DEBUG:-false}"
WORKERS="${API_WORKERS:-1}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LinearRAG API Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到python3命令${NC}"
    exit 1
fi

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
python3 -c "import fastapi, uvicorn, jinja2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    pip install -q fastapi uvicorn jinja2 python-multipart
fi

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}警告: 未设置OPENAI_API_KEY环境变量${NC}"
    echo "请运行: export OPENAI_API_KEY=\"your-api-key\""
fi

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo "  主机: $HOST"
echo "  端口: $PORT"
echo "  调试模式: $DEBUG"
echo ""

# 启动服务
exec python3 -m uvicorn api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload "$DEBUG" \
    --workers "$WORKERS"
