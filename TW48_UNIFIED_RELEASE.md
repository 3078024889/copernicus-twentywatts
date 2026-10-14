# TW48｜统一离线研究正式总包：交付范围与限制

2026-10-12。已在隔离环境进行全量单元测试、实验账本篡改/重启测试、CPU 配对实验历史复核及本机 HTTP 服务验证。**Windows 实机和 GitHub main 均未在这里执行。**

## 小说原著约束

《哥白尼》关于树突节点连接、七千多学习算法变异体、特殊分层训练环境、并行 AI 与学习规则自我改进提供研究问题；固定回放、资源账本、SHA-256 证据验证与自主调度属于工程方案，不是原文给出的算法公式。

## 本版实质交付

1. TW33–TW47 全部研究算法、双生回测、主动行为指纹、学习策略元记忆、多代变异、关联分支、CPU 回测与原著研究索引整合保留。
2. TW48 新增 `tw10/research_journal.py`，完整批次/研究摘要追加记账，进程重启恢复调度计数，SHA-256 逐条检查，SQLite 全账校验，HTTP 页面独立展示实际记录。研究报告按照批次生成不可覆盖的独立文件。
3. `scripts/VERIFY_AND_START_TW48_WINDOWS.ps1`：先验收源数据、完整回归测试、状态检查、端口占用，再于 28724 并行启动，不停 V3 或旧 28723。`SYNC_MAIN_WINDOWS.ps1` 在本机 Git 目录干净时才复制源码、验收并提交推送。
4. 用 SQLite backup API 生成静态、可校验的实验数据库快照；真实计算状态不与旧 V3 Mother/Blackbox 合并。母版与认证仍锁定。

## 真实科研状态与禁止夸大

- 7777 是已经登记的变异体定义/旧全池配置；新关联算法的行为独立性审计尚未达到 7777/7777。组合探针目前最多区分 6581 种行为。
- TW47 两批 CPU 对照在 ±10% 窗口内 44/48；资源可比较实验的迁移均值仍为负，**没有通过学习效果认证**。
- 12 个独立 AI 的正式认证 0/12；未在真实 Mother、真实跨知识库盲测和 Windows 长期压力实验中证明超越。
- 旧 V3 继续暂停；历史证据不可删除。远程仓库截至上次用户实际推送的基线为 e849351；本包未擅自标注 main 已同步。

## Windows 首次上线（与现有 28723 并行）

完整解压至新目录。打开 PowerShell：

```powershell
$Root = 'D:\TWENTYWATTS_TW48_UNIFIED_MASTER\TWENTYWATTS_UNIFIED_MASTER'
powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\VERIFY_AND_START_TW48_WINDOWS.ps1" -Port 28724 -PythonExe 'C:\Python314\python.exe'
```

浏览器进入 `http://127.0.0.1:28724/`。工作进程按设定间隔自动推进，网页是只读接口。

通过 Windows 真实长测后，如要推送 main，先确保本地 Git checkout 干净，再调用总包内 `SYNC_MAIN_WINDOWS.ps1`。不要把旧 28723 正在使用的 SQLite 文件原地覆盖；需要切换服务时先分别确认 PID、端口和数据库路径。
