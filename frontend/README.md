# Family Hub 前端

> 🏠 治愈系家庭管理Web应用 - 前端项目

## 技术栈

- **框架**: Vue 3.4+ (Composition API)
- **构建工具**: Vite 5+
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **样式**: SCSS + CSS Variables
- **图标**: Lucide Icons
- **HTTP客户端**: Axios
- **实时通信**: Socket.io-client

## 设计风格

采用 **Kawaii 治愈系** 设计风格：
- 🍑 主色调：蜜桃粉 (#FFB5BA)
- 🥛 背景色：奶油米色 (#FFF5E6)
- 🌿 成功色：薄荷绿 (#B8E5D8)
- 💜 辅助色：薰衣草紫 (#E8DFF5)
- 🧸 圆角设计，营造柔和感
- ✨ 细腻的过渡动画

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 项目结构

```
src/
├── assets/
│   └── styles/          # SCSS 样式文件
│       ├── variables.scss   # 设计系统变量
│       ├── mixins.scss      # SCSS混合
│       └── global.scss      # 全局样式
├── components/
│   ├── common/          # 通用组件
│   │   ├── BaseButton.vue
│   │   ├── BaseCard.vue
│   │   ├── BaseInput.vue
│   │   ├── BaseModal.vue
│   │   ├── Avatar.vue
│   │   ├── EmptyState.vue
│   │   ├── LoadingSpinner.vue
│   │   └── ToastContainer.vue
│   └── layout/          # 布局组件
│       ├── AppHeader.vue
│       ├── AppSidebar.vue
│       └── BottomNav.vue
├── layouts/
│   ├── DefaultLayout.vue    # 主布局
│   └── AuthLayout.vue       # 认证页面布局
├── pages/               # 页面组件
│   ├── auth/
│   │   ├── LoginPage.vue
│   │   └── RegisterPage.vue
│   ├── shopping/
│   │   ├── ShoppingListPage.vue
│   │   └── ShoppingDetailPage.vue
│   ├── expenses/
│   │   ├── ExpenseListPage.vue
│   │   ├── ExpenseAddPage.vue
│   │   ├── ExpenseStatsPage.vue
│   │   └── IncomeListPage.vue
│   ├── chores/
│   ├── shop/
│   ├── trips/
│   ├── DashboardPage.vue
│   └── SettingsPage.vue
├── router/              # 路由配置
├── stores/              # Pinia 状态管理
│   ├── user.ts
│   ├── shopping.ts
│   ├── expense.ts
│   └── ui.ts
├── types/               # TypeScript 类型定义
├── utils/               # 工具函数
│   ├── api.ts           # API 配置
│   └── formatters.ts    # 格式化函数
├── App.vue
└── main.ts
```

## 功能模块

### ✅ 已完成
- [x] 设计系统（颜色、字体、间距、动画）
- [x] 通用组件库（Button、Card、Modal、Input、Avatar等）
- [x] 响应式布局（桌面端侧边栏 + 移动端底部导航）
- [x] 深色模式支持
- [x] 认证页面（登录/注册）
- [x] 仪表盘首页
- [x] 购物清单模块
- [x] 记账模块（支出列表、添加支出）
- [x] 设置页面

### 🚧 开发中
- [ ] 家务管理模块
- [ ] 积分商城模块
- [ ] 旅行预算模块
- [ ] 统计图表
- [ ] 实时同步 (Socket.io)

## 环境变量

创建 `.env` 文件：

```env
VITE_API_URL=http://localhost:8000/api
```

## 开发规范

### 组件命名
- 页面组件：`XxxPage.vue`
- 通用组件：`BaseXxx.vue` 或首字母大写
- 布局组件：`XxxLayout.vue`

### 样式规范
- 使用 SCSS 变量（定义在 `variables.scss`）
- 使用 BEM 命名法
- 响应式优先（移动端优先）

### 状态管理
- 使用 Pinia Composition API 风格
- 按功能模块划分 store

## 与后端对接

前端通过 RESTful API 与后端通信：
- 开发环境通过 Vite proxy 代理 API 请求
- 生产环境需要配置正确的 `VITE_API_URL`

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## License

MIT
