# Seraphim Trading System - 重构计划

## 📋 项目概述

Seraphim（原Vanilla）是一个个人/小团队使用的加密货币和股票量化交易系统。本次重构旨在简化架构，提高开发效率，并增加实际交易功能。

## 🎯 重构目标

- **简化架构**：从微服务改为单体架构，减少系统复杂度
- **去除Go后端**：将指标计算等功能迁移到Python/Django
- **现代化前端**：升级到 Tailwind CSS + Alpine.js + TradingView Charts
- **增强功能**：添加真实交易、回测、策略开发功能
- **优化部署**：简化Docker配置，提高部署效率

## 🏗️ 技术栈选择

### 最终技术栈
```yaml
Trading Platforms: 
  - Kraken (Crypto) 
  - IBKR (Stocks)
  
Frontend: 
  - Django Templates
  - Tailwind CSS
  - Alpine.js  
  - TradingView Lightweight Charts
  
Backend:
  - Django 4.2+ (Monolith)
  - Django REST Framework
  - Django Channels (WebSocket)
  - Celery (异步任务)
  
Database & Cache:
  - PostgreSQL (主数据库)
  - Redis (缓存 + Celery broker + Channels layer)
  
ASGI Server: Uvicorn
Dependency Management: Poetry + requirements.txt
Deployment: Docker + AWS Lightsail
Bot: 简化的Telegram Bot (可选)
```

### Python库依赖
```yaml
Trading & Data:
  - ccxt (统一交易所API) 
  - ib-insync (IBKR API)
  - TA-Lib (技术指标)
  - pandas, numpy (数据处理)
  
Web Framework:
  - Django 4.2+
  - channels, channels-redis
  - celery, redis
  - uvicorn
  
Frontend:
  - 通过CDN引入 Tailwind, Alpine.js, TradingView Charts
```

## 🔄 重构阶段

### Phase 1: 清理和准备工作 ✅
- [x] 分析现有系统架构
- [x] 设计新系统架构
- [x] 确定技术栈
- [x] 移动旧代码到legacy (`bot/` → `legacy/old_bot/`, `gobackend/` → `legacy/gobackend/`)
- [x] 更新docker-compose.yml（移除go和bot服务）
- [x] 创建Poetry项目配置（pyproject.toml）
- [x] 更新requirements.txt（兼容现有依赖 + 新增交易API）
- [x] 更新Dockerfile和entrypoint.sh（Python 3.11 + Uvicorn支持）

### Phase 2: 核心后端重构 🔄
- [ ] 设置Poetry依赖管理
- [ ] 移植Go指标计算到Python
- [ ] 集成Kraken API
- [ ] 集成IBKR API  
- [ ] 添加Celery异步任务
- [ ] 升级WebSocket到Uvicorn

### Phase 3: 前端现代化 ⏳
- [ ] 引入Tailwind CSS
- [ ] 集成Alpine.js
- [ ] 实现TradingView Lightweight Charts
- [ ] 重新设计交易界面
- [ ] 实现响应式设计

### Phase 4: 功能增强 ⏳
- [ ] 实现策略开发框架
- [ ] 添加回测系统
- [ ] 实现真实交易功能
- [ ] 投资组合管理
- [ ] 风险管理系统

### Phase 5: 部署和优化 ⏳
- [ ] 简化Docker配置
- [ ] 简化Telegram Bot
- [ ] 性能优化
- [ ] 监控和日志
- [ ] 文档完善

## 📊 数据模型保留

现有的数据模型设计良好，基本保留：
- `SymbolInfo` - 交易对信息
- `OhlcPrice` - OHLC价格数据  
- `OhlcPriceMinute` - 分钟级价格数据
- `Indicator` - 技术指标
- `UserProfile` - 用户信息
- `UserOrder`, `UserTrade` - 交易相关
- `Portfolio` - 投资组合

## 🔧 具体执行步骤

### 步骤 1: 项目结构重组
```bash
seraphim/
├── legacy/              # 旧代码备份
│   ├── gobackend/      # 已移动
│   └── old_bot/        # 将移动
├── web/                # Django主应用
├── pyproject.toml      # Poetry配置
├── requirements.txt    # 生产环境依赖
└── SERAPHIM_REFACTOR_PLAN.md
```

### 步骤 2: 设置Poetry
```bash
cd seraphim
poetry init
poetry add django channels celery redis ib-insync ccxt talib pandas
poetry add --group dev pytest black flake8
```

### 步骤 3: Go功能迁移清单
```python
需要迁移的Go功能：
- indicators.go → Python TA-Lib
- data_service.go → Django Models + Celery tasks
- messaging.go → Django Channels + Celery
- repositories.go → Django ORM
```

### 步骤 4: API集成顺序
1. Kraken WebSocket (实时价格)
2. Kraken REST API (历史数据、交易)
3. IBKR ib-insync集成
4. 数据同步和存储

### 步骤 5: 前端升级计划
1. 安装Tailwind CSS (via CDN)
2. 引入Alpine.js
3. 实现TradingView Charts
4. 重新设计交易界面

## 🚨 注意事项

### 数据迁移
- 现有PostgreSQL数据保持不变
- Go计算的指标数据可以重新计算
- 用户数据和历史交易数据务必保留

### API配置
- 确保IBKR API已申请并测试
- 确保Kraken API权限配置正确
- 先用测试环境验证所有功能

### 安全考虑
- API密钥使用环境变量
- 交易功能先在Paper Trading测试
- 实现适当的风险控制

## 📈 成功指标

### Phase 1完成标准：
- [x] 旧代码已移动到legacy
- [x] 新架构文档完成
- [x] 技术栈确定

### Phase 2完成标准：
- [ ] Django项目可以正常运行
- [ ] Kraken API可以获取实时数据
- [ ] IBKR API可以获取股票数据
- [ ] 基础技术指标计算正常

### Phase 3完成标准：
- [ ] 现代化UI界面完成
- [ ] 实时价格图表显示正常
- [ ] 响应式设计在移动端正常

### 最终完成标准：
- [ ] 可以执行真实交易
- [ ] 回测功能正常工作
- [ ] 策略可以自动执行
- [ ] 系统稳定运行

## 📝 更新日志

- **2025-10-05**: 初始重构计划创建
- **2025-10-05**: Phase 1 完成 - 架构设计和清理
  - ✅ 移动legacy代码 (`bot/` → `legacy/old_bot/`)
  - ✅ 更新docker-compose.yml（移除go/bot服务）
  - ✅ 创建pyproject.toml和更新requirements.txt
  - ✅ 升级Dockerfile（Python 3.11 + Uvicorn）
  - ✅ API申请指南（IBKR + Kraken）
  - ✅ Docker系统测试成功 - 所有容器正常运行
  - ✅ 清理不需要的目录和大文件：
    - 🗑️ 删除 `.idea/`, `.vscode/` (IDE配置)
    - 📦 移动 `bin/` → `legacy/go_bin/` (Go工具, 54MB) → 🗑️ 已删除
    - 📦 移动 `pkg/` → `legacy/go_pkg/` (Go modules, 188MB) → 🗑️ 已删除
    - 🗑️ 删除 `gobackend`二进制文件 (7MB)
    - 🗑️ 删除所有`.DS_Store`文件
    - 💾 **节省空间：249MB → 128KB (99.9%减少)**

---

> 🚀 让我们开始Seraphim的重构之旅！
