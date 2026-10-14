# TW54 — 固定入口与原生 D 系列部署审计

## 基线和原著约束
原著《哥白尼》明确支持多种学习算法变异体、树突关联网络、长期分层学习与学习算法自我改进作为研究目标，但没有公开 7777 变异生成公式或十二席认证公式。TW54 延续 TW53 的 D 系列初代真实训练，保留所有失败记录与 Mother 锁定。

## 此轮新增
- `tw10.dendrite_native.verify_all`：从真实 SQLite 中核对 7777 初代基因型、每个检查点哈希与对应拓扑、每个候选步数与其训练记录数量、逐条学习记录哈希、所有后代试验哈希、收录后代的父子对应关系和子代状态哈希。只在启动与显式维护时深度审计，网页高频轮询只读轻量摘要。
- `offline_oracle.py`：服务启动前全量验证 D 证据；页面区分原生训练轮次、服务批次、后代试验及后代续训轮次，清楚显示完整审计状态，不把旧周期 CPU 科研当作 D 系列主实验。
- `scripts/migrate_native_state.py`：通过 SQLite 在线备份接口完成一致性快照，验证新旧 V8 源身份，并在替换新目录检查点前归档当前快照；保留旧安装目录，不执行删除操作。
- `scripts/SWITCH_TO_FIXED_28720_WINDOWS.ps1`：明确要求操作人员先 CTRL+C 停止旧 `28727`；检查 `28720`、`28727` 均未监听后执行迁移，再在 Windows 运行所有自动测试、SQLite 验证，最后**只启动一个 `28720` 服务**。任何验收失败直接拦截上线。
- `tests/test_tw54_native_release.py`：独立验证全池完整性、篡改拒绝、D 进度核算和最新状态迁移。

## 与真实长期实验相关的限制
初代定义是 7777 份可执行算子程序，不是 7777 个经科学证明独立的算法。长期进化仍使用合成任务、预定义算子变异与试验性选择集门槛；暂收后代不是认证后代；正式认证保持 0/12。真实 Mother 尚未迁入。当前资源调度限制每批候选和后代续训数量，不能保证固定 20W 功率或 CPU 完全等额。完整的跨真实知识库知识发现和统计认证仍待研发。

## Windows 固定入口切换（重要）
1. 解压 `TWENTYWATTS_TW54_FIXED_ORACLE_FULL_MASTER_20261013.zip` 到 `D:\TWENTYWATTS_TW54_FIXED_ORACLE_FULL_MASTER_20261013`，子目录须包含 `TWENTYWATTS_UNIFIED_MASTER`。
2. 原 `28727` TW53 PowerShell 窗口按 **Ctrl+C** 停止；不要终止或删除 V3 Mother/Blackbox 数据，不要手工复制正在写入的 sqlite。
3. 新开 PowerShell，执行：

```powershell
$New = 'D:\TWENTYWATTS_TW54_FIXED_ORACLE_FULL_MASTER_20261013\TWENTYWATTS_UNIFIED_MASTER'
$Old = 'D:\TWENTYWATTS_TW53_NATIVE_DENDRITE_FULL_MASTER_20261013\TWENTYWATTS_UNIFIED_MASTER'
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "$New\scripts\SWITCH_TO_FIXED_28720_WINDOWS.ps1" `
  -PreviousRoot $Old -PythonExe 'C:\Python314\python.exe' `
  -Participants 64 -Interval 5
```

4. 打开固定地址 http://127.0.0.1:28720/ 。后续继续使用这个地址，不再以改端口当成升级。
5. 如果提示端口被占用，脚本**不会自动杀任何进程**，请先确认端口持有者。若测试失败，也不会启动固定服务。
6. 旧 TW53 目录和原始训练状态不会删除；新目录的旧状态存档在 `migration_archive` 目录，迁移审计文件保留具体摘要。

## 本环境验收与实机界限
在隔离环境完成全回归测试、现有 D 快照的完整哈希验证、SQLite 迁移模拟和 HTTP 接口检查。Windows 最终切换需要用户电脑上实测，不能冒称已部署或 GitHub main 已推送。
