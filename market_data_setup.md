# IBKR市场数据订阅指南

## 当前状态
- ✅ IBKR Paper Trading账户 (DU2101016)
- ✅ 个人用途 (选择 Non-Professional)
- ✅ 4个交易符号需要数据

## 数据订阅建议

### 免费数据包 (推荐激活)
- **US Securities Snapshot Bundle** - 覆盖: TSLA, IAU
- **IDEALPRO Forex** - 覆盖: XAUUSD (现货黄金)

### 付费数据包 (可选)
- **US Index Data Bundle** (~$4/月) - 覆盖: DJI (道琼斯指数)

## 设置步骤

1. **登录IBKR Client Portal**
2. **进入 Settings > Market Data Subscriptions**
3. **选择 "Non-Professional" 状态**
4. **激活免费数据包**:
   - US Securities Snapshot and Futures Value Bundle
   - IDEALPRO Forex Bundle
5. **考虑订阅指数数据** (如果需要DJI实时数据)

## 验证方法

在完成订阅后，运行以下命令测试数据可用性:

```bash
# 检查IBKR连接状态
docker compose logs ib-gateway --tail 20

# 验证Dashboard显示
curl http://localhost:8000/api/market-data/?symbol=TSLA&interval=86400

# 重启服务刷新数据
docker compose restart web
```

## 预期结果

- ✅ TSLA, IAU: 免费延迟数据 (15-20分钟)
- ✅ XAUUSD: 免费外汇数据
- 💰 DJI: 需要付费实时数据 (或使用免费延迟数据)

## Paper Trading优势

Paper Trading账户通常包含:
- 主要股票的延迟数据
- 基础外汇数据  
- ETF数据
- 可能无需额外付费即可满足开发需求

## 费用总结

- **最低费用**: $0/月 (仅使用免费数据)
- **推荐配置**: ~$4/月 (包含指数实时数据)
- **完整配置**: ~$10/月 (所有实时数据)

对于个人交易系统开发，推荐先使用免费数据测试系统，确认需求后再考虑付费订阅。
