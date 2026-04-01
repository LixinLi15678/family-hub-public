#!/bin/bash
# ============================================
# Family Hub - self-hosted deployment script
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 参数解析
UPDATE_MODE=false
TEST_MODE=false
GIT_BRANCH="main"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --update|-u)
            UPDATE_MODE=true
            ;;
        --test|-t)
            UPDATE_MODE=true    # 测试模式默认执行更新流程
            TEST_MODE=true
            ;;
        --branch|-b)
            shift
            GIT_BRANCH="${1:-main}"
            ;;
        *)
            echo -e "${YELLOW}⚠️  未识别参数: $1${NC}"
            echo "用法: ./deploy.sh [--update|-u] [--test|-t] [--branch|-b <name>]"
            exit 1
            ;;
    esac
    shift
done

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
if [ "$UPDATE_MODE" = true ]; then
    if [ "$TEST_MODE" = true ]; then
        echo -e "${BLUE}║     🧪 Family Hub test deployment script        ║${NC}"
    else
        echo -e "${BLUE}║     🔄 Family Hub update deployment script          ║${NC}"
    fi
else
    echo -e "${BLUE}║     🏠 Family Hub deployment script               ║${NC}"
fi
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# 检查依赖
# ============================================
echo -e "${YELLOW}[1/7] 检查依赖...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装！${NC}"
    echo "请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ Node.js 未安装！${NC}"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}✅ 依赖检查通过${NC}"

# ============================================
# Get server IP
# ============================================
echo ""
echo -e "${YELLOW}[2/7] Get server IP...${NC}"

# 尝试获取IP
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
if [ -z "${SERVER_IP}" ]; then
    SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
fi

if [ -z "$SERVER_IP" ]; then
    SERVER_IP="127.0.0.1"
    echo -e "${YELLOW}⚠️  无法自动获取局域网 IP，已回退到 ${SERVER_IP}${NC}"
fi

echo -e "${GREEN}✅ Server IP: ${SERVER_IP}${NC}"

# ============================================
# 备份数据库（更新模式）
# ============================================
if [ "$UPDATE_MODE" = true ]; then
    echo ""
    echo -e "${YELLOW}[3/7] 备份数据库...${NC}"
    
    # 检查服务是否运行
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        mkdir -p backups
        
        if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; then
            docker-compose -f docker-compose.prod.yml exec -T db \
                pg_dump -U postgres family_hub > "backups/${BACKUP_FILE}" 2>/dev/null || true
            
            if [ -f "backups/${BACKUP_FILE}" ] && [ -s "backups/${BACKUP_FILE}" ]; then
                echo -e "${GREEN}✅ 数据库已备份: backups/${BACKUP_FILE}${NC}"

                # 清理旧备份（只保留最近10次）
                BACKUP_KEEP=10
                if compgen -G "backups/backup_*.sql" > /dev/null; then
                    backup_files_sorted=($(ls -1t backups/backup_*.sql 2>/dev/null || true))
                    if [ "${#backup_files_sorted[@]}" -gt "$BACKUP_KEEP" ]; then
                        for old_backup in "${backup_files_sorted[@]:$BACKUP_KEEP}"; do
                            rm -f "$old_backup" || true
                        done
                        echo -e "${GREEN}✅ 已清理旧备份，保留最近 ${BACKUP_KEEP} 个${NC}"
                    fi
                fi
            else
                echo -e "${YELLOW}⚠️  数据库备份跳过（可能是首次部署）${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  数据库未运行，跳过备份${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  服务未运行，跳过备份${NC}"
    fi
fi

# ============================================
# 拉取最新代码（更新模式）
# ============================================
if [ "$UPDATE_MODE" = true ]; then
    echo ""
    echo -e "${YELLOW}[4/7] 拉取最新代码...${NC}"
    
    if [ -d ".git" ]; then
        # 避免因前端构建导致 package-lock.json 产生本地改动而阻断更新
        if ! git diff --quiet -- "frontend/package-lock.json" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  检测到 frontend/package-lock.json 有本地改动，已自动恢复以便拉取最新代码${NC}"
            git restore "frontend/package-lock.json" 2>/dev/null || git checkout -- "frontend/package-lock.json" 2>/dev/null || true
        fi

        if git pull origin "$GIT_BRANCH"; then
            echo -e "${GREEN}✅ 代码已更新${NC}"
        else
            echo -e "${YELLOW}⚠️  Git pull 失败，继续使用当前代码${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  非 Git 仓库，跳过代码更新${NC}"
    fi
fi

# ============================================
# 配置环境变量
# ============================================
echo ""
if [ "$UPDATE_MODE" = true ]; then
    echo -e "${YELLOW}[5/7] 检查环境变量...${NC}"
else
    echo -e "${YELLOW}[3/7] 配置环境变量...${NC}"
fi

# 如果 .env 不存在，创建它
if [ ! -f ".env" ]; then
    # Generate a random JWT key and require an explicit database password
    JWT_KEY=$(openssl rand -hex 32)
    echo -e "${YELLOW}未检测到 .env，开始创建。${NC}"
    read -s -p "Set a database password: " DB_PASSWORD
    echo ""
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}❌ 数据库密码不能为空${NC}"
        exit 1
    fi

    cat > .env << EOF
DB_PASSWORD=${DB_PASSWORD}
JWT_SECRET_KEY=${JWT_KEY}
EOF

    echo -e "${GREEN}✅ 环境变量已创建${NC}"
else
    # 检查 JWT_SECRET_KEY 是否存在
    if ! grep -q "JWT_SECRET_KEY" .env; then
        JWT_KEY=$(openssl rand -hex 32)
        echo "JWT_SECRET_KEY=${JWT_KEY}" >> .env
        echo -e "${GREEN}✅ JWT密钥已添加到环境变量${NC}"
    else
        echo -e "${GREEN}✅ 环境变量已存在${NC}"
    fi
fi

# 读取 .env 变量（如 DB_PASSWORD/JWT_SECRET_KEY）
if [ -f ".env" ]; then
    # shellcheck disable=SC1091
    set -a
    source .env
    set +a
fi

# 确认数据库密码已设置，避免与现有数据卷密码不一致
if [ -z "${DB_PASSWORD}" ]; then
    echo -e "${RED}❌ 未检测到 DB_PASSWORD，请在项目根目录 .env 中设置 DB_PASSWORD 并与数据库实际密码保持一致。${NC}"
    echo -e "${YELLOW}提示: 如果数据库容器已在运行，可用命令查看当前密码: docker compose -f docker-compose.prod.yml exec db env | grep POSTGRES_PASSWORD${NC}"
    exit 1
fi

# ============================================
# 构建前端
# ============================================
echo ""
if [ "$UPDATE_MODE" = true ]; then
    echo -e "${YELLOW}[6/7] 重新构建前端（可能需要几分钟）...${NC}"
else
    echo -e "${YELLOW}[4/7] 构建前端（可能需要几分钟）...${NC}"
fi

cd frontend

# 创建生产环境配置（use same-origin API via nginx reverse proxy)
cat > .env.production << EOF
VITE_API_URL=/api/v1
EOF

# 安装依赖并构建
if [ -f "package-lock.json" ]; then
    npm ci --silent
else
    npm install --silent
fi
npm run build

cd ..

echo -e "${GREEN}✅ 前端构建完成${NC}"

# ============================================
# 启动/更新Docker服务
# ============================================
echo ""
if [ "$UPDATE_MODE" = true ]; then
    echo -e "${YELLOW}[7/7] 更新服务...${NC}"
    
    # 停止旧服务
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # 重新构建并启动
    docker-compose -f docker-compose.prod.yml up -d --build
    
    echo -e "${GREEN}✅ 服务已更新${NC}"
else
    echo -e "${YELLOW}[5/7] 启动服务...${NC}"
    
    docker-compose -f docker-compose.prod.yml up -d --build
    
    echo -e "${GREEN}✅ 服务已启动${NC}"
fi

# 等待服务启动
echo "等待服务启动..."
sleep 10

# ============================================
# 初始化/更新数据库
# ============================================
echo ""
echo -e "${YELLOW}[数据库迁移] 运行数据库迁移...${NC}"

# 等待后端容器就绪（最多 60 秒）
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker-compose -f docker-compose.prod.yml ps backend 2>/dev/null | grep -q "backend"; then
        if docker-compose -f docker-compose.prod.yml ps backend | grep -q "Up"; then
            break
        fi
    fi
    sleep 5
    WAITED=$((WAITED + 5))
done

MIGRATION_DB_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@db:5432/family_hub"
if docker-compose -f docker-compose.prod.yml ps backend | grep -q "Up"; then
    if docker-compose -f docker-compose.prod.yml exec -T backend env DATABASE_URL="${MIGRATION_DB_URL}" alembic upgrade head; then
        echo -e "${GREEN}✅ 数据库迁移完成${NC}"
    else
        echo -e "${RED}❌ 数据库迁移失败，请查看日志并重试${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  后端容器未启动，跳过迁移${NC}"
    echo -e "${YELLOW}提示: 可手动执行 docker-compose -f docker-compose.prod.yml exec -T backend env DATABASE_URL=\"${MIGRATION_DB_URL}\" alembic upgrade head${NC}"
fi

# ============================================
# 测试（仅测试模式）
# ============================================
if [ "$TEST_MODE" = true ]; then
    echo ""
    echo -e "${YELLOW}[测试] 运行后端测试...${NC}"
    if docker-compose -f docker-compose.prod.yml exec -T backend pytest -q; then
        echo -e "${GREEN}✅ 后端测试通过${NC}"
    else
        echo -e "${RED}❌ 后端测试失败，请检查日志${NC}"
        exit 1
    fi
fi


# ============================================
# 验证服务
# ============================================
echo ""
echo -e "${YELLOW}[验证] 检查服务状态...${NC}"

# 检查服务是否运行
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ 所有服务运行正常${NC}"
    
    # 测试后端健康检查
    sleep 3
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 后端API正常${NC}"
    else
        echo -e "${YELLOW}⚠️  后端API可能还在启动中，请稍后检查${NC}"
    fi
else
    echo -e "${RED}❌ 部分服务启动失败，请检查日志${NC}"
    echo -e "${YELLOW}查看日志: docker-compose -f docker-compose.prod.yml logs${NC}"
fi

# ============================================
# 完成
# ============================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
if [ "$UPDATE_MODE" = true ]; then
    echo -e "${GREEN}║     🎉 更新部署成功！                  ║${NC}"
else
    echo -e "${GREEN}║     🎉 部署成功！                      ║${NC}"
fi
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "访问地址："
echo -e "  🏠 应用主页: ${BLUE}http://${SERVER_IP}${NC}"
echo -e "  📖 API文档:  ${BLUE}http://${SERVER_IP}:8000/api/docs${NC}"
echo ""
echo -e "Other devices on the same network can open a browser and visit the address above."
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo -e "  - 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo -e "  - 停止服务: docker-compose -f docker-compose.prod.yml down"
echo -e "  - 重启服务: docker-compose -f docker-compose.prod.yml restart"
if [ "$UPDATE_MODE" = true ]; then
    echo -e "  - 查看备份: ls -lh backups/"
fi
echo ""
