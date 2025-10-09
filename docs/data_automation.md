# 数据自动更新系统

## 概述

Seraphim 使用 Celery + Redis 实现数据的自动化更新和计算。

## 架构

```
┌─────────────┐      ┌──────────────┐      ┌───────────────┐
│   Django    │─────→│    Redis     │←─────│ Celery Worker │
│     Web     │      │   (Broker)   │      │   (任务执行)  │
└─────────────┘      └──────────────┘      └───────────────┘
       │                     ↑
       │                     │
       └──────────────┬──────┘
                      │
              ┌───────┴──────────┐
              │   Celery Beat    │
              │   (定时调度器)   │
              └──────────────────┘
```

## 定时任务

系统每小时自动执行以下任务：

| 时间 | 任务 | 说明 |
|------|------|------|
| :05  | fetch_ohlc_data | 从 Kraken 获取最新 OHLC 数据 |
| :10  | calculate_indicators | 计算技术指标 (RSI, MACD, SMA, EMA, ADX) |
| :15  | calculate_ema_channel | 计算 EMA Channel (EMA High/Low 33) |
| :20  | calculate_market_regime | 计算市场状态 (trending/ranging) |
| :25  | generate_trading_signals | 生成交易信号 |

## 手动触发更新

### 方法 1: API 端点 (推荐)

```bash
# 更新所有数据（按顺序执行）
curl -X POST "http://localhost:8082/api/manual-update/?task=all"

# 仅更新 OHLC 数据
curl -X POST "http://localhost:8082/api/manual-update/?task=ohlc"

# 仅计算指标
curl -X POST "http://localhost:8082/api/manual-update/?task=indicators"

# 仅计算 EMA Channel
curl -X POST "http://localhost:8082/api/manual-update/?task=ema"

# 仅计算市场状态
curl -X POST "http://localhost:8082/api/manual-update/?task=regime"

# 仅生成交易信号
curl -X POST "http://localhost:8082/api/manual-update/?task=signals"
```

**响应示例**：
```json
{
    "status": "success",
    "message": "Full data update started (all tasks)",
    "task_id": "abc123-def456-ghi789",
    "task_type": "all"
}
```

### 方法 2: 查询任务状态

```bash
# 使用返回的 task_id 查询任务状态
curl "http://localhost:8082/api/manual-update/?task_id=abc123-def456-ghi789"
```

**响应示例**：
```json
{
    "task_id": "abc123-def456-ghi789",
    "status": "SUCCESS",
    "ready": true,
    "successful": true,
    "result": {
        "ohlc": {"status": "success", "output": "..."},
        "indicators": {"status": "success", "output": "..."}
    },
    "error": null
}
```

### 方法 3: Django Shell

```python
from api.tasks import manual_update_all

# 同步执行（阻塞）
result = manual_update_all()

# 异步执行（推荐）
task = manual_update_all.delay()
print(f"Task ID: {task.id}")

# 检查任务状态
print(f"Status: {task.status}")
print(f"Result: {task.result if task.ready() else 'Still running...'}")
```

## 服务管理

### 启动所有服务

```bash
docker compose up -d
```

这会启动：
- `web`: Django 应用
- `celery-worker`: Celery 任务执行器
- `celery-beat`: Celery 定时调度器
- `redis`: 消息队列
- `postgres`: 数据库

### 查看日志

```bash
# 查看 Celery Worker 日志
docker compose logs -f celery-worker

# 查看 Celery Beat 日志
docker compose logs -f celery-beat

# 查看所有服务日志
docker compose logs -f
```

### 重启服务

```bash
# 重启 Celery Worker
docker compose restart celery-worker

# 重启 Celery Beat
docker compose restart celery-beat

# 重启所有服务
docker compose restart
```

## 监控

### Celery 任务监控

可以使用 Flower (Celery 监控工具):

```bash
# 添加到 docker-compose.yml (可选)
flower:
  image: mher/flower
  command: celery --broker=redis://redis:6379/0 flower --port=5555
  ports:
    - "5555:5555"
  depends_on:
    - redis
    - celery-worker
```

然后访问 http://localhost:5555 查看任务执行情况。

### Redis 监控

```bash
# 连接到 Redis CLI
docker compose exec redis redis-cli

# 查看所有 keys
KEYS *

# 查看队列长度
LLEN celery

# 监控 Redis 命令
MONITOR
```

## 故障排查

### 任务没有执行

1. 检查 Celery Worker 是否运行：
```bash
docker compose ps celery-worker
```

2. 检查 Celery Beat 是否运行：
```bash
docker compose ps celery-beat
```

3. 查看 Worker 日志：
```bash
docker compose logs celery-worker --tail=50
```

### 任务执行失败

1. 查看任务详细错误：
```bash
docker compose logs celery-worker | grep ERROR
```

2. 手动执行 Python 脚本测试：
```bash
docker compose exec web python scripts/fetch_historical_data.py
```

### Redis 连接问题

```bash
# 测试 Redis 连接
docker compose exec web python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0); print(r.ping())"
```

## 性能优化

### 并发执行

修改 `docker-compose.yml`，增加 Worker 并发数：

```yaml
celery-worker:
  command: celery -A seraphim worker --loglevel=info --concurrency=4
```

### 任务优先级

在 `seraphim/celery.py` 中配置任务优先级：

```python
app.conf.task_routes = {
    'api.tasks.generate_trading_signals': {'queue': 'high_priority'},
    'api.tasks.fetch_ohlc_data': {'queue': 'normal'},
}
```

## 开发建议

### 添加新任务

1. 在 `api/tasks.py` 中定义新任务：

```python
@shared_task(bind=True, name='api.tasks.my_new_task')
def my_new_task(self):
    logger.info("Starting my new task...")
    # ... 任务逻辑
    return {'status': 'success'}
```

2. 在 `seraphim/celery.py` 中添加定时调度（可选）：

```python
app.conf.beat_schedule = {
    'my-new-task-daily': {
        'task': 'api.tasks.my_new_task',
        'schedule': crontab(hour='0', minute='0'),  # 每天 00:00
    },
}
```

### 测试任务

```python
# 测试任务是否可以被发现
from api.tasks import my_new_task

# 同步执行（测试）
result = my_new_task()
print(result)

# 异步执行（生产）
task = my_new_task.delay()
print(f"Task ID: {task.id}")
```

## 生产环境建议

1. **使用 Redis 持久化**：
   - 在 `docker-compose.yml` 中添加 `appendonly yes`

2. **限制任务超时**：
   - 已设置：`CELERY_TASK_TIME_LIMIT = 30 * 60` (30分钟)

3. **任务失败重试**：
```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def my_task(self):
    pass
```

4. **监控和告警**：
   - 使用 Flower 监控任务执行
   - 配置 Sentry 捕获错误

5. **日志轮转**：
   - 配置 Docker 日志大小限制

```yaml
services:
  celery-worker:
    logging:
      options:
        max-size: "10m"
        max-file: "3"
```

## 参考资料

- [Celery 官方文档](https://docs.celeryproject.org/)
- [Redis 官方文档](https://redis.io/documentation)
- [Django Celery Integration](https://docs.celeryproject.org/en/stable/django/)

