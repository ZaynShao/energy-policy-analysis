# launchd 安装指南 — weekly_audit

## 安装

```bash
# 1. 拷 plist 到用户级 LaunchAgents
cp _meta/launchd/com.shaoziyuan.policy-vault-weekly-audit.plist \
   ~/Library/LaunchAgents/

# 2. 加载到 launchd
launchctl load ~/Library/LaunchAgents/com.shaoziyuan.policy-vault-weekly-audit.plist

# 3. 验证(应见对应 label)
launchctl list | grep policy-vault
```

## 触发(测试)

```bash
launchctl start com.shaoziyuan.policy-vault-weekly-audit
# 跑完看日志:
tail -50 _meta/audit/launchd.log
# 看产出:
cat _meta/audit/audit_state.json
ls -la _meta/audit/weekly_summary_*.md
```

## 卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.shaoziyuan.policy-vault-weekly-audit.plist
rm ~/Library/LaunchAgents/com.shaoziyuan.policy-vault-weekly-audit.plist
```

## 调度规则

每周日 9:00 跑(`StartCalendarInterval: Weekday=0, Hour=9, Minute=0`)。

错过(电脑关机/睡眠)→ launchd 默认不补跑(`RunAtLoad=false`)。
要立刻跑用 `launchctl start <label>` 手动触发。

## cron 替代(如果不想用 launchd)

```bash
crontab -e
# 加这行:
0 9 * * 0 cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析" && /usr/bin/python3 _meta/scripts/weekly_audit.py && /usr/bin/python3 _meta/scripts/audit_alert.py >> _meta/audit/launchd.log 2>&1
```

## 阈值告警(参 PHASE2_PLAYBOOK §1)

`audit_alert.py` 检查:
- 矩阵覆盖率单周下降 > 5%
- citation_gap 单周新增 > 50
- isolated 政策单周 +20
- P0 主题(VPP/储能/电力市场/V2G/聚合商/配电网) × P0 省(京沪苏浙粤鲁)零命中

告警追加到 `_meta/audit/audit_alerts.md`,退出码 1 → 配 launchd 邮件 / 通知 hook 可二次扩展。
