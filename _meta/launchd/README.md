# launchd 安装指南

本目录提供 2 个 launchd plist:

| plist | 频率 | 跑什么 | 日志 |
|---|---|---|---|
| `com.shaoziyuan.policy-vault-weekly-audit.plist` | 每周日 9:00 | weekly_audit + audit_alert(B1.4) | `_meta/audit/launchd.log` |
| `com.shaoziyuan.policy-vault-daily-queries.plist` | 每天 6:00 | gen_daily_queries(B1.5,产 50 query plan) | `_meta/audit/launchd_daily.log` |

# weekly_audit

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

---

# daily_queries(B1.5)

`gen_daily_queries.py` 读 `coverage_matrix.json`(weekly_audit 产),
按"覆盖度最低 + P0 主题加权 + P0 省加权"选 50 cells × 1 query,
输出到 `_l2_rebuild_state/daily_queries/daily_<date>.jsonl`(gitignore'd)。

## 安装

```bash
cp _meta/launchd/com.shaoziyuan.policy-vault-daily-queries.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.shaoziyuan.policy-vault-daily-queries.plist
```

## 接 Tavily API arm(可选,配 API key 后)

当前 plist 只跑生成器。**实际抓取需要 Tavily API key**,改 plist 命令:

```xml
<string>cd "$VAULT" &amp;&amp; \
  /usr/bin/python3 _meta/scripts/gen_daily_queries.py &amp;&amp; \
  /usr/bin/python3 _meta/audit_2026-05-06/run_tavily_matrix.py \
    --queries _l2_rebuild_state/daily_queries/daily_$(date +%Y-%m-%d).jsonl &amp;&amp; \
  /usr/bin/python3 _meta/audit_2026-05-06/fetch_candidates.py &amp;&amp; \
  /usr/bin/python3 _meta/audit_2026-05-06/normalize_to_raw.py</string>
```

并在 plist `EnvironmentVariables` 节加:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>TAVILY_API_KEY</key>
    <string>tvly-XXXX</string>
</dict>
```

入库后跑 trigger A 全套(rel_judge + 5C)。如果是无人值守 daily,trigger A 那段是 LLM 调用,
需要 Claude Code 后台 daemon 能调 API — 通常做法是把 daily 限制到 query 生成 + 抓取 +
normalize 入 staging,LLM 部分走人工触发(每周 / 每两周一次)。

## 调度规则

每天 06:00 跑(电脑睡眠 → launchd 默认不补跑)。错过手动:
```bash
launchctl start com.shaoziyuan.policy-vault-daily-queries
```
