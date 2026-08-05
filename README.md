# 钉钉 AI BI 看板

PMS → 钉钉 AI 表格 数据同步工具

---

## 安装 dws CLI（首次使用）

```cmd
npm install -g --allow-scripts=dingtalk-workspace-cli dingtalk-workspace-cli
dws auth login
```

---

## 运行模式

### 1. 增量同步（默认，最近 3 天）

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN"
```

> 物料/仓库：全量同步 + 清孤儿  
> 订单/明细/库存：仅最近 3 天

### 2. 全量同步

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN" --full
```

> 所有表全量拉取，库存正常更新（含 status 映射）

### 3. 指定日期

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN" --date 2026-08-01
```

> 仅同步 8 月 1 日的数据

### 4. 指定天数

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN" --days 7
```

> 同步最近 7 天

### 5. 仅预览不写入

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN" --dry-run
```

> 与其他参数自由组合：`--full --dry-run`、`--date 2026-08-01 --dry-run`

### 6. 指定 dws 路径

```cmd
pms_sync.exe --token "Bearer YOUR_TOKEN" --dws-path "D:\npm-global\dws.cmd"
```

---

## 各表同步策略

| 表 | 增量模式 | 全量模式 | 去重 key |
|---|---------|---------|----------|
| 物料 | 全量 + 清孤儿 | 全量 + 清孤儿 | `num`（物料编号） |
| 仓库 | 全量 + 清孤儿 | 全量 + 清孤儿 | `code`（仓库编码） |
| 订单主表 | 目标日期 | 全量 | `orderId` |
| 订单明细 | 跟订单 | 全量 | `detailId` |
| 库存变动 | 目标日期 + skip | 全量更新 | `recordNum`（记录编号） |

---

## 数据源

- **PMS**: `https://pms.cosmos-ag.com` (baseId=152)
- **AI 表格**: `vNG4YZ7Jnlp30gY2HNoGqLr9W2LD0oRE`

## 日志

每次运行自动在 `pms_sync.exe` 同级目录 `logs/` 下生成 `sync_YYYYMMDD_HHMMSS.log`

---

## Windows 定时任务

`任务计划程序` → 创建基本任务 → 每天凌晨 2:00 → 启动程序 `pms_sync.exe`，参数 `--token "Bearer TOKEN"`
