# 🏠 Family Hub - 家庭治愈管家

<p align="center">
  <img src="frontend/public/favicon.svg" alt="Family Hub Logo" width="120" height="120">
</p>

<p align="center">
  <strong>面向 2-5 人家庭的协作式生活管理应用</strong>
</p>

<p align="center">
  购物清单 · 家庭记账 · 家务奖励 · 钻石商城 · 旅行预算
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite-42b883" alt="Frontend">
  <img src="https://img.shields.io/badge/backend-FastAPI-009688" alt="Backend">
  <img src="https://img.shields.io/badge/database-PostgreSQL-336791" alt="Database">
  <img src="https://img.shields.io/badge/deploy-Docker%20Compose-2496ED" alt="Docker Compose">
  <img src="https://img.shields.io/github/v/release/LixinLi15678/family-hub-public?display_name=tag" alt="Release">
</p>

> 轻量、自托管、适合家庭成员共同使用的协作式生活管理应用。
>
> 支持购物清单、家庭记账、家务奖励、钻石商城、旅行预算等模块，适合 2-5 人家庭在局域网或自建服务器中长期使用。

## 快速导航

- [✨ 项目亮点](#项目简介)
- [🚀 快速开始](#快速开始)
- [🧩 功能概览](#功能概览)
- [🛠 手动部署说明](#手动部署说明)
- [🔐 安全建议](#安全建议)
- [🗂 项目结构](#项目结构)
- [💻 本地开发](#本地开发)
- [⭐ Star History](#star-history)

---
## 项目简介

Family Hub 是一个围绕家庭日常协作设计的全栈应用，适合自托管部署，供 2-5 位家庭成员共同使用。

当前项目包含以下核心模块：

- **购物清单**：支持多清单、分类管理、多人协作
- **家庭记账**：支持三级分类、多币种、费用分摊与统计
- **家务管理**：支持任务看板、重复任务、钻石奖励
- **钻石商城**：支持奖励兑换、商品上架、购买记录
- **旅行预算**：支持预算规划、支出跟踪与汇总

项目采用前后端分离架构：

- **前端**：Vue 3 + Vite + Pinia + TypeScript
- **后端**：FastAPI + SQLAlchemy + Socket.IO
- **数据库**：PostgreSQL 15
- **部署方式**：Docker Compose + Nginx

---

## 功能概览

| 模块 | 说明 | 当前状态 |
|------|------|----------|
| 🛒 购物清单 | 多清单管理、按商店分类、实时协作 | ✅ 可用 |
| 💰 家庭记账 | 三级分类、多币种、费用分摊、统计分析 | ✅ 可用 |
| 🧹 家务管理 | 任务看板、重复任务、奖励机制 | ✅ 可用 |
| 🎁 钻石商城 | 商品兑换、记录管理、奖励消费 | ✅ 可用 |
| ✈️ 旅行预算 | 预算规划、支出追踪、汇总统计 | ✅ 可用 |

### 钻石与等级说明

- **钻石余额**：主要通过完成家务或奖励行为获取，在商城中消耗
- **等级体系**：基于累计消费计算
  - 商城消费会计入累计消费
  - 记账支出会按汇率换算成人民币后，以 `1 RMB = 10 钻石` 计入累计消费
  - 若启用了费用分摊，则累计消费归属到分摊成员，而非付款人
- **展示位置**：设置页、首页成员卡片、右上角用户菜单中会显示等级与进度

---

## 快速开始

如果你准备在一台长期运行的自托管设备上部署，推荐先阅读本文档，再根据自己的环境选择脚本部署或手动部署。

### 方式一：一键部署（推荐）

```bash
cd ~/family-hub
./deploy.sh
```

脚本会自动完成：

1. 检查 Docker / Node.js 依赖
2. 获取服务器局域网 IP
3. 生成或补全 `.env`
4. 构建前端
5. 启动数据库、后端、前端容器
6. 执行数据库迁移
7. 输出局域网访问地址

### 更新部署

```bash
cd ~/family-hub
./deploy.sh --update
```

更新流程会自动执行：

- 备份数据库（若服务已运行，保留最近 10 份）
- 拉取最新代码
- 重建前端
- 重启服务
- 执行数据库迁移

### deploy.sh 参数说明

| 参数 | 说明 |
|------|------|
| `--update` / `-u` | 更新模式：备份 → git pull → 重建 → 迁移 |
| `--test` / `-t` | 更新模式 + 部署完成后运行后端测试 |
| `--branch <name>` / `-b <name>` | 指定 git pull 的分支（默认 `main`） |

---

## 运行环境要求

部署前请确保机器上已安装：

- **Docker Desktop**（macOS）或可用的 Docker + Docker Compose 环境
- **Node.js / npm**
- **Git**（通常系统已预装）

可先执行以下命令检查：

```bash
docker --version
docker-compose --version
npm --version
git --version
```

---

## 部署架构

```text
                    ┌─────────────────────────────────────┐
                    │            外部访问（可选）          │
                    │    通过 Tailscale / 内网穿透接入      │
                    └──────────────┬──────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────┐
│                             家庭局域网                               │
│                                  │                                  │
│    ┌─────────┐  ┌─────────┐  ┌──┴───────┐  ┌─────────┐             │
│    │  Phone  │  │  Tablet │  │  Server  │  │ Desktop │             │
│    │ Browser │  │ Browser │  │ Self-host│  │ Browser │             │
│    └────┬────┘  └────┬────┘  └──────────┘  └────┬────┘             │
│         │            │            │              │                  │
│         └────────────┴─────┬──────┴──────────────┘                  │
│                            │                                        │
│                    http://<server-ip>                             │
└─────────────────────────────────────────────────────────────────────┘
```

容器职责如下：

- **db**：PostgreSQL 15
- **backend**：FastAPI + Socket.IO API 服务
- **frontend**：Nginx 托管前端构建产物

---

## 手动部署说明

如果你不想使用一键脚本，也可以手动完成部署。

### 1）克隆项目

```bash
cd ~
git clone <your-repository-url> family-hub
cd family-hub
```

### 2）配置环境变量

项目根目录下创建 `.env`：

```bash
cat > .env << 'EOF'
DB_PASSWORD=your-db-password
JWT_SECRET_KEY=your-random-secret-key
EOF
```

建议使用随机密钥：

```bash
openssl rand -hex 32
```

> 注意：如果数据库卷已经存在，后续修改 `DB_PASSWORD` 时要确保和数据库当前密码保持一致，否则后端将无法连接数据库。

### 3）构建前端

部署脚本会自动写入 `frontend/.env.production`，其格式如下：

```bash
VITE_API_URL=http://<server-ip>/api/v1
```

手动构建示例：

```bash
cd frontend
# 将 IP 替换为服务器的实际局域网 IP
echo "VITE_API_URL=http://<server-ip>/api/v1" > .env.production
npm ci
npm run build
cd ..
```

### 4）启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 5）执行数据库迁移

```bash
docker-compose -f docker-compose.prod.yml exec -T backend \
  env DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@db:5432/family_hub" \
  alembic upgrade head
```

### 6）验证服务

```bash
curl http://localhost:8000/health
```

预期返回类似：

```json
{"status":"healthy","service":"Family Hub"}
```

---

## 默认访问方式

部署成功后，局域网内设备可通过以下地址访问：

- **应用主页**：`http://<server-ip>`
- **API 文档**：`http://<server-ip>:8000/api/docs`

你可以通过以下命令获取当前服务器 IP：

```bash
ipconfig getifaddr en0
```

Linux 常见方式：

```bash
hostname -I | awk '{print $1}'
```

macOS 可尝试：

```bash
ipconfig getifaddr en0
```

---

## 局域网部署建议

### 建议为服务器设置固定 IP

为了避免设备重启或路由器重新分配地址后前端 API 地址失效，建议给部署机器配置固定局域网 IP。

可选方式：

1. **在路由器中做 DHCP 绑定**（推荐）
2. **在 macOS 中设置静态 IP**

如果 IP 发生变化，需要重新构建前端，使 `VITE_API_URL` 与新的地址保持一致。

---

## 外网访问（可选）

如果希望在外网访问，可以使用 **Tailscale**、反向代理或其他安全隧道方案。

### 推荐原因

- 配置简单
- 相对安全
- 适合家庭设备互联
- 无需直接暴露家庭公网端口

### 基本步骤

1. 在服务器上安装 Tailscale
2. 在手机、平板、电脑上安装 Tailscale
3. 使用同一个账号登录
4. 通过分配到的 `100.x.x.x` 地址访问服务

例如：

```text
http://100.x.x.x
```

启用 MagicDNS 后，也可用设备名访问。

---

## 安全建议

- **不要暴露 PostgreSQL 5432 端口到公网**
- 为 `DB_PASSWORD` 和 `JWT_SECRET_KEY` 使用强随机值
- 若对公网开放访问，请在反向代理或入口层配置 **HTTPS**
- `.env`、数据库备份、上传目录、日志文件不要提交到公共仓库
- 在首次公开前，轮换任何可能曾进入 git 历史的真实密钥


## 数据与持久化

当前生产部署中使用了两个 Docker Volume：

- `postgres_data`：保存 PostgreSQL 数据
- `uploads_data`：保存上传文件（如商品图片等）

这意味着：

- 容器重建后数据不会因容器删除而直接丢失
- 只要不主动删除 volume，数据库与上传文件可保留

> 注意：执行 `docker-compose down -v` 会同时删除卷数据，请谨慎使用。

---

## 常用运维命令

### 查看服务状态

```bash
docker-compose -f docker-compose.prod.yml ps
```

### 查看日志

```bash
# 查看全部日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看后端日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs -f db
```

### 重启服务

```bash
docker-compose -f docker-compose.prod.yml restart
```

### 停止服务

```bash
docker-compose -f docker-compose.prod.yml down
```

### 重新构建并启动

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 数据库备份与恢复

### 手动备份

```bash
docker-compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U postgres family_hub > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢复备份

```bash
cat backup_20241203_120000.sql | docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres family_hub
```

### 使用部署脚本自动备份

执行以下命令时：

```bash
./deploy.sh --update
```

脚本会在服务已运行且数据库可用的前提下，自动将备份写入项目目录下的 `backups/` 文件夹，并默认只保留最近 **10** 份备份。

---

## 历史记账数据回填（等级累计消费）

如果你是从旧版本升级到带“等级/累计消费”逻辑的新版本，并希望历史记账数据也纳入累计消费，可在迁移后执行回填脚本。

### dry-run

```bash
docker-compose -f docker-compose.prod.yml exec -T backend \
  python scripts/backfill_expense_diamond_spends.py --dry-run
```

### 全量重建回填

```bash
docker-compose -f docker-compose.prod.yml exec -T backend \
  python scripts/backfill_expense_diamond_spends.py --reset-all
```

---

## 开机自启动建议

### 方式一：使用 Docker Desktop 自动启动（推荐）

1. 打开 Docker Desktop
2. 进入 Settings > General
3. 启用 **Start Docker Desktop when you log in**
4. 项目中的容器设置了 `restart: always`，Docker 恢复后服务会随之启动

### 方式二：自定义启动脚本（备选）

```bash
cat > ~/start-family-hub.sh << 'EOF'
#!/bin/bash
cd ~/family-hub
docker-compose -f docker-compose.prod.yml up -d
EOF

chmod +x ~/start-family-hub.sh
```

然后将其加入系统登录项。

---

## 常见问题排查

### 1. 局域网其他设备无法访问主页

优先检查：

```bash
docker-compose -f docker-compose.prod.yml ps
ipconfig getifaddr en0
curl http://localhost:8000/health
```

还需要确认：

- 服务器与访问设备处于同一局域网
- macOS 防火墙未拦截对应端口
- 当前访问 IP 与前端构建时使用的 IP 一致

---

### 2. 页面能打开，但接口请求失败

通常是前端中的 `VITE_API_URL` 配置与实际 IP 不一致。

检查：

```bash
cd frontend
cat .env.production
```

如需修复：

```bash
npm run build
cd ..
docker-compose -f docker-compose.prod.yml restart frontend
```

如果希望最省事，直接重新执行：

```bash
./deploy.sh
```

---

### 3. 数据库连接失败

检查数据库容器：

```bash
docker-compose -f docker-compose.prod.yml ps db
docker-compose -f docker-compose.prod.yml logs db
```

还应确认：

- `.env` 中的 `DB_PASSWORD` 是否存在
- `DB_PASSWORD` 是否与已有数据库卷中的密码一致
- 后端容器是否已成功启动

---

### 4. 更新时迁移失败

可先查看日志：

```bash
docker-compose -f docker-compose.prod.yml logs -f backend
```

也可手动执行迁移：

```bash
docker-compose -f docker-compose.prod.yml exec -T backend \
  env DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@db:5432/family_hub" \
  alembic upgrade head
```

---

### 5. 如何完全重置

⚠️ **以下操作会删除数据库和上传文件，请务必先备份。**

```bash
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

然后重新执行数据库迁移。

---

## 项目结构

```text
family-hub/
├── backend/                    # FastAPI 后端
│   ├── app/                    # 应用代码
│   ├── migrations/             # Alembic 迁移文件
│   ├── tests/                  # 测试代码
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # Vue 3 前端
│   ├── public/
│   ├── src/
│   ├── dist/                   # 构建产物
│   └── package.json
├── backups/                    # 更新脚本自动生成的数据库备份（如存在）
├── docker-compose.yml          # 开发环境配置
├── docker-compose.prod.yml     # 生产环境配置
├── nginx.conf                  # Nginx 配置
├── deploy.sh                   # 一键部署 / 更新脚本
├── IMPROVEMENT-TASKS.md        # 开发任务清单
└── README.md                   # 项目说明
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3、Vite、Pinia、Vue Router、TypeScript、Axios、Socket.IO Client、Chart.js |
| 后端 | FastAPI、SQLAlchemy、Alembic、python-socketio、APScheduler |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose、Nginx |

---

## 适合谁使用

这个项目更适合以下场景：

- 家庭内部共用的生活管理系统
- 使用一台常开设备做家庭服务器
- 希望通过浏览器在手机、平板、电脑上统一访问
- 希望后续逐步扩展到外网访问或更完整的家庭数字中枢

---

## 本地开发

```bash
# 启动后端 + 数据库（开发环境）
docker-compose up -d

# 启动前端开发服务器
cd frontend
npm install
npm run dev
```

---

<p align="center">Made with ❤️ for families</p>

---

## Star History

<p align="center">
  <a href="https://www.star-history.com/#LixinLi15678/family-hub-public&Date">
    <img src="https://api.star-history.com/svg?repos=LixinLi15678/family-hub-public&type=Date" alt="Star History Chart">
  </a>
</p>
