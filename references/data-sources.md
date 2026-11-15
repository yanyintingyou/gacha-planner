# 数据源：Gachabase

## 目录

1. 定位
2. 分支与可信度归属
3. URL 结构
4. 六类页面能取到什么
5. 取值方式
6. 关键字段
7. 跟踪测试服改动
8. 常见误读
9. 复核

## 1. 定位

gachabase.net 是社区维护的解包数据库，覆盖原神、绝区零、星铁。角色面板、技能倍率、命座、武器精炼、套装效果、突破材料都来自游戏客户端，每轮数据修订留档。

它提供数值与文本，不提供卡池排期。谁在哪一版、上半还是下半 up，仍以官方前瞻与游戏内公告为准。

## 2. 分支与可信度归属

| 分支 | 内容 | 在规划里算什么 |
|---|---|---|
| release | 正式服已上线数据 | 事实，可直接引用 |
| beta | 测试服包，数值仍可能改 | 推断，引用时标“测试服” |
| creator | 创作服，仅绝区零，数据运行时加载 | 用不上 |

页面头部标着当前分支的数据版本与修订号，形如 `v7.2.51 (BETA)`、`D49319249 | R49319249`。引用具体数值时带上修订号，下一版调整了能对上。

同一游戏 beta 与 release 的差集，是“测试服已有、正式服未上线”的候选名单，用于提前预留资源。差集只说明这些内容存在于测试包，落在哪一版要另找证据。

## 3. URL 结构

原神（`gi.gachabase.net`）：

| 内容 | 路径 |
|---|---|
| 角色列表 | `/characters/{branch}?lang=zh-cn` |
| 武器列表 | `/weapons/{branch}?lang=zh-cn` |
| 圣遗物列表 | `/artifacts/{branch}?lang=zh-cn` |
| 角色详情 | `/characters/{id}/{slug}/{branch}` |
| 武器详情 | `/weapons/{id}/{slug}/{branch}` |
| 圣遗物详情 | `/artifacts/{id}/{slug}/{branch}` |
| 历史快照 | `/characters/{id}/{slug}/beta/7.2.50/49190139` |
| 两版差异 | `/diff/characters/{id}/{slug}?prev=beta_7.2.50_49190139&cur=beta_7.2.51_49319249` |
| 更新日志 | `/changelog/beta` |

绝区零（`zzz.gachabase.net`）同构，板块名不同：`/agents`（代理人）、`/w-engines`（音擎）、`/drive-discs`（驱动盘）、`/bangboo`、`/items`、`/enemies`，另有原神没有的 `/timeline/beta`。

`{id}` 是游戏内数字 ID，只给 slug 会 404。语言参数 `lang=zh-cn` 与 `lang=chs` 输出一致。

## 4. 六类页面能取到什么

| 页面 | 列表里已有的 | 要不要进详情页 |
|---|---|---|
| 原神角色 | 名字、稀有度、元素、武器类型、ID、图标 | 要，天赋倍率与命座只在详情页 |
| 原神武器 | 上述 + 白值/副词条 + 五档精炼全文 + 突破材料 | 不用 |
| 原神圣遗物 | 上述 + 二件套/四件套效果全文 + 五部位 ID | 不用 |
| 绝区零代理人 | 名字、S/A 级、属性、职业、阵营、十项基础面板、首次版本 | 要，技能与意象影画只在详情页 |
| 绝区零音擎 | 上述 + 基础/进阶属性 + 五阶效果全文 + 专武归属 | 不用 |
| 绝区零驱动盘 | 上述 + 二件套/四件套效果全文 | 不用 |

结论：判断专武值不值得抽、新套装是什么定位，抓一次列表页就够；判断新角色是主 C 还是拐，必须逐条进详情页读倍率与命座。

## 5. 取值方式

列表页由客户端渲染，HTML 里没有条目文本，数据全在页面尾部一段内嵌的 SvelteKit payload 里。取文本得到空列表。

详情页是服务端渲染，去掉标签就能读到属性、天赋、命座、材料、描述。

站点没有公开 API。`api.gachabase.net` 是站内自用的内部接口，未文档化。

脚本 `scripts/gachabase.py` 把这两条路径包好：

```bash
python scripts/gachabase.py gi char                 # 原神角色列表
python scripts/gachabase.py gi weapon               # 武器列表
python scripts/gachabase.py gi artifact             # 圣遗物列表
python scripts/gachabase.py zzz char                # 绝区零代理人
python scripts/gachabase.py zzz weapon              # 音擎
python scripts/gachabase.py zzz disc                # 驱动盘
python scripts/gachabase.py gi char release         # 正式分支
python scripts/gachabase.py gi char danica          # 单角色页文本
python scripts/gachabase.py zzz weapon 13022 en     # 指定语言，默认 zh-cn
```

列表输出三列：ID、slug、名字，可直接拿去查详情。详情查询认 ID、slug 或列表里显示的名字；原神武器的列表名是英文，用中文查不到，先按英文名定位。

## 6. 关键字段

原神角色记录没有版本信息：`release_date` 与 `release_version` 全表恒为 `null`。判断某角色属于哪一版，只能看更新日志里首次以 `NEW` 出现的修订，或对比 beta 与 release 的差集。

绝区零记录带版本，可直接读 `first_seen{version,design_revision,design_timestamp}` 与 `last_updated{...}`。

音擎多一个 `signature_agent_id`，标明这件音擎为谁设计，省掉靠名字猜专武归属。基础与进阶属性是 `base_stat` / `advanced_stat`（`stat_id` + 数值），比读面板文字可靠。

## 7. 跟踪测试服改动

1. `/changelog/beta` 按修订倒序列出该轮涉及的角色、武器、套装，标 `NEW` 或 `UPDATED`，每条带 `See Changes` 直连差异页。
2. `/diff/...?prev=&cur=` 给两版逐字段差异，倍率、描述、属性变化的数值对比。版本对不上会 404，用日志里的链接最稳。
3. `/timeline/beta`（仅绝区零）按日历排每次修订，区分「公布」与「测试」。公布早于测试约一版本。

判断新角色落点：原神回看日志里它首次 `NEW` 的修订，绝区零读 `first_seen.version`。

## 8. 常见误读

- **筛选是纯前端**。`?filter=r%3A5` 只改浏览器显示，payload 始终全量。页面看到的是子集，不代表数据源只有这些。
- **原神武器列表只有英文名**。`lang` 对该列表不生效，payload 里没有中文字段，中文名要进详情页取。角色、套装、音擎的列表都有中文名。
- **UI 标签翻译不全**。中文页里仍有 `Set Bonuses`、`2-Piece Set`、`Artifact Set`、`First Added`，正文是中文。
- **占位条目**。原神武器有 `name:null` 的废案（18 条），绝区零音擎有名字为 `...` 的未译条目，旅行者四形态的名字引用变量取不到。这些对规划没用。
- **同 slug 多条目**。故事武器存在多状态版本，slug 相同，会被合并。
- **数字有时效**。条目数每版增长，不要沿用上次记的数。
- **抓取礼貌**。站点 robots 对 AI 训练类 UA 全线禁止，对普通读取放行。批量取页控制频率。

## 9. 复核

每次规划前先跑一次列表命令，确认当前分支版本与条目数，再引用具体数值。

2026-11-15 实测基线，只用来判断解析是否正常：原神 beta 124 角色 / 269 武器 / 65 套圣遗物，release 122 / 266 / 63；绝区零 beta 68 代理人 / 171 音擎 / 32 套驱动盘，release 66 / 165 / 30。
