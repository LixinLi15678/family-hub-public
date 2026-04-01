# Family Hub Backend

家庭管理应用后端服务 - Kawaii Family Hub

## 技术栈

- **框架**: FastAPI >= 0.100
- **ORM**: SQLAlchemy >= 2.0
- **数据库**: PostgreSQL >= 15
- **实时通信**: python-socketio >= 5.0
- **异步服务器**: Uvicorn >= 0.23
- **任务调度**: APScheduler >= 3.10
- **认证**: PyJWT >= 2.8

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── scheduler.py         # 定时任务
│   ├── models/              # SQLAlchemy模型
│   ├── schemas/             # Pydantic模式
│   ├── routers/             # API路由
│   ├── services/            # 业务逻辑
│   ├── socket/              # Socket.io处理
│   └── utils/               # 工具函数
├── migrations/              # Alembic迁移
├── tests/                   # 测试
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 快速开始

### 使用 Docker Compose (推荐)

```bash
# 启动所有服务 (数据库 + 后端)
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

### 本地开发

1. 创建虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：

```bash
cp env.example .env
# 编辑 .env 文件配置数据库等参数
```

4. 启动 PostgreSQL 数据库

5. 运行数据库迁移：

```bash
alembic upgrade head
```

6. 启动开发服务器：

```bash
uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## API 端点总览

### 认证 `/api/v1/auth`
- POST `/register` - 用户注册
- POST `/login` - 用户登录
- POST `/refresh` - 刷新Token
- POST `/logout` - 登出

### 家庭管理 `/api/v1/families`
- POST `/` - 创建家庭
- GET `/me` - 获取当前家庭
- POST `/join` - 加入家庭
- GET `/members` - 获取成员列表
- PUT `/invite-code` - 更新邀请码

### 购物清单 `/api/v1/shopping`
- GET/POST `/stores` - 商店管理
- GET/POST `/lists` - 清单管理
- GET/POST/PATCH/DELETE `/items` - 商品管理

### 记账 `/api/v1/expenses`
- GET/POST `/categories` - 分类管理
- GET/POST/PUT/DELETE `/` - 支出记录
- POST `/{id}/splits` - 费用分摊
- GET `/stats/monthly` - 月度统计

### 收入 `/api/v1/incomes`
- GET/POST/PUT/DELETE `/` - 收入记录
- GET `/stats/monthly` - 月度统计

### 汇率 `/api/v1/currencies`
- GET `/` - 获取货币列表
- GET `/exchange-rates` - 获取汇率
- POST `/exchange-rates/refresh` - 刷新汇率

### 家务 `/api/v1/chores`
- GET/POST/PUT/DELETE `/` - 家务任务
- POST `/{id}/complete` - 完成任务
- GET `/history` - 完成历史

### 钻石商城 `/api/v1/products`
- GET/POST/PUT/DELETE `/` - 商品管理
- POST `/{id}/purchase` - 购买商品

### 旅行预算 `/api/v1/trips`
- GET/POST/PUT/DELETE `/` - 旅行计划
- POST `/{id}/budgets` - 预算分配
- POST `/{id}/expenses` - 旅行支出
- GET `/{id}/stats` - 预算统计

### 用户 `/api/v1/users`
- GET/PATCH `/me` - 个人信息
- GET `/me/points` - 钻石余额
- GET `/me/transactions` - 钻石流水
- GET `/me/purchases` - 已购商品

## Socket.io 事件

### 购物清单
- `shopping:item_added` - 商品添加
- `shopping:item_updated` - 商品更新
- `shopping:item_checked` - 商品勾选
- `shopping:item_deleted` - 商品删除

### 记账
- `expense:created` - 支出创建
- `expense:updated` - 支出更新
- `expense:deleted` - 支出删除

### 家务
- `chore:created` - 任务创建
- `chore:completed` - 任务完成
- `chore:updated` - 任务更新

### 钻石
- `points:updated` - 钻石更新
- `product:purchased` - 商品购买

## 定时任务

| 任务 | 频率 | 描述 |
|------|------|------|
| 汇率更新 | 每6小时 | 从API获取最新汇率 |
| 钻石过期 | 每日凌晨 | 清理90天未使用钻石 |
| 重复家务 | 每日凌晨 | 生成周期性家务任务 |
| 数据备份 | 每日凌晨 | 备份数据库 |

## 测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率报告的测试
pytest --cov=app tests/
```

## 部署

### Self-hosted deployment

1. 安装 Docker 和 Docker Compose
2. 克隆项目到服务器
3. 配置 `.env` 文件
4. 运行 `docker-compose up -d`

### 生产环境注意事项

- 更改 `JWT_SECRET_KEY` 为强随机字符串
- 配置 PostgreSQL 数据库密码
- 设置正确的 `CORS_ORIGINS`
- 配置 HTTPS
- 设置日志记录

## License

MIT
