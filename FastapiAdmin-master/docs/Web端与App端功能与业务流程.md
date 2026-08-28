# 智慧胸痛中心管理平台 · Web 端 / App 端功能与业务流程全览

> 全面梳理 Web 管理端（frontend/web）与 App 医生端（frontend/app）全部功能模块、业务流程、端间协同。v3.1.0，基于真实代码与接口。

---

## 〇、总览：两端定位与共享底座

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│   Web 管理端 (5180)          │        │   App 医生端 (5190)          │
│   admin 运营 / 审核员辅助      │        │   医生 / 审核员（移动端）      │
│   「管」：配置、审核、统计、发布 │        │   「用」：填报、随访、学习、AI  │
└──────────────┬──────────────┘        └──────────────┬──────────────┘
               │             同一套 REST API             │
               └─────────────► /api/v1/cpx/* ◄──────────┘
                              FastAPI + MySQL + Redis
```

- **数据完全互通**：两端共用同一数据库（20 张业务表）与同一接口层，无独立数据副本
- **权限三档**：`管理员(admin)` / `审核员(auditor)` / `医生(doctor)`，接口级 `BusinessRole` 隔离
- **Web 主责"管理配置"**，**App 主责"业务执行"**，二者通过病例/模板/公告/增值服务等数据协同

---

## 一、Web 端功能清单与业务流程

### 1.1 功能总览

| 层级 | 模块 | 页面 | 角色 | 一句话定位 |
|---|---|---|---|---|
| 业务 | **首页驾驶舱** | `views/cpx/dashboard` | admin | 全中心运行数据可视化 |
| 业务 | **病例管理** | `views/cpx/case` | admin | 全量病例总览/详情/删除（双视图） |
| 业务 | **模板管理** | `views/cpx/template` | admin | 动态表单模板配置（字段/分类/发布） |
| 业务 | **审核管理** | `views/cpx/audit` | admin / **auditor** | **审核员审核操作**（工作台/待审/通过/驳回/记录），Web 独有 |
| 业务 | **医院管理** | `views/cpx/hospital` | admin | 医院 CRUD/启停 |
| 业务 | **用户管理** | `views/cpx/user`（api） | admin | 医生/审核员账号管理（页面复用框架用户页） |
| 业务 | **胸痛学院** | `views/cpx/academy` | admin | 学习资源（PPT/视频/文档）管理发布 |
| 业务 | **公告管理** | `views/cpx/announcement` | admin | 公告发布/下线（App 首页展示） |
| 业务 | **增值服务管理** | `views/cpx/value_added` | admin | 服务卡片配置（App 首页展示） |
| 业务 | **系统日志** | `views/cpx/log` | admin | 操作留痕查询 |
| 框架 | **后台管理** | `views/module_system/*` | 超管 | 菜单/角色/部门/字典/参数/岗位/用户/通知/工单/版本/聊天 |
| 通用 | **登录/异常** | `login` / `exception` | - | 认证与错误页 |

### 1.2 核心功能业务流程

#### ① 首页驾驶舱
```
登录 → GET /cpx/stats/dashboard
→ 4 张统计卡（医院/用户/病例/审核，数字滚动 + 骨架屏）
→ 3 图表：病例趋势（日/月切换）、审核环图（通过率%）、医院排行 Top10
→ 运行概览 4 格（医院运行/医生团队/审核进度/今日动态）
```
- 数据流向：`stats.service.dashboard()` 实时聚合 5 张业务表（hospital/user_account/case_record/audit_record）→ 无缓存、每次刷新实时
- 关键节点：数字滚动动画、趋势图日/月 Tab 切换、刷新按钮
- 关联：所有业务数据最终在此体现（病例数↑=医生填报多；通过率=审核员工作）

#### ② 病例管理（admin 视角）
```
列表（医院卡片总览 ⇄ 病例表格双视图）→ 搜索/筛选（状态/医院/日期）
→ 详情查看（基础信息 + form_data 动态表单 + 审核记录）
→ 删除（级联删除 case_detail/audit_record/follow_up/ecg_consult）
```
- 数据流向：`/cpx/case/list|detail|delete` → case_record 主表 + case_detail JSON
- 关键节点：级联删除保护（删病例连带删关联数据）；admin 可查看**全部医院**病例（医生只能看自己的）
- 关联：与 App 填报数据同源；Web 侧重"总览/治理"，App 侧重"填报/执行"

#### ③ 模板管理（Web 独有核心）
```
列表 → 新建模板（名称+版本，默认未发布、无字段）
→ 【添加字段 / 复制标准模板(copy-standard)】→ 字段分类管理（tab 增删/重命名）
→ 发布 →（App 端可见可用）
```
- 数据流向：`/cpx/template/*` → report_template + template_field
- 关键节点：**新模板无字段**，必须复制标准字段或手动添加；发布后才对 App 生效；**已被病例使用的模板禁止取消发布**（防数据错乱，新建版本解决）
- 关联：模板 = App 填报表单的"图纸"，改模板不影响已存 form_data（JSON 宽松存储）

#### ④ 医院 / 用户管理
```
医院：列表/新增/编辑/批量启停 → hospital 表
用户：新增医生（自动建 doctor_info 档案）/新增审核员（automatic auditor_info）
    /改信息/重置密码/批量启停 → user_account + role
```
- 关键节点：医生必须归属医院；启停联动登录（禁用即无法登录）
- 关联：医生账号是 App 登录与病例归属的基础

#### ⑤ 公告管理 / 增值服务管理（Web 发布 → App 展示）
```
公告：新建（标题/副标题/富文本内容/类型/排序）→ 发布(published) → App 首页公告栏轮播
     → 下线(offline) / 删除
增值服务：新建（名称/副标题/图标/封面/跳转类型+URL/排序）→ 上线(online)
     → App 首页增值服务大卡（点击跳 H5/外链/App 内页）
```
- 关键节点：`status` 状态机（draft→published/online→offline）；App 只读 `active` 接口自动过滤非发布项
- 关联：**典型的两端协同**——Web 配置运营内容，App 消费展示

#### ⑥ 胸痛学院（Web 发布 → App 学习）
```
上传资源（PPT/视频/PDF，POST /upload）→ 填标题/分类/简介 → 发布
→ App 端 academy 列表/详情（浏览量+1）
```

#### ⑦ 系统日志
```
列表 + 按角色筛选 → system_log 表（写操作自动留痕：module/operation/result/IP）
```

#### ⑧ 框架后台（module_system，FastapiAdmin 自带）
`菜单管理/角色/部门/字典/参数/岗位/系统用户/通知/工单/版本发布/聊天/AI 认证`——通用后台能力，与胸痛业务模块解耦，由超管维护。

---

## 二、App 端功能清单与业务流程

### 2.1 功能总览（主包 13 页 + 分包 8 页）

| 页面 | 定位 | 角色 | 核心接口 |
|---|---|---|---|
| `index` 首页工作台 | 统计 + 快捷入口 | 医生 | doctor/stats + announcement/active + value-added/active |
| `work` 数据直报 | 病例列表 + 填报 | 医生 | doctor/case/* |
| `case` 病例详情/表单 | 病例填报与查看 | 医生 | doctor/case/{id} |
| `followup` 随访管理 | 随访计划执行 | 医生 | doctor/followup/* |
| `analysis` 数据分析 | 个人数据概览 | 医生 | doctor/stats/overview |
| `unit` 救治医院 | 救治单元列表 | 医生 | doctor/units |
| `meeting` 三会模板 | 会议 PPT 生成 | 医生 | doctor/meeting/templates |
| `academy` 胸痛学院 | 学习资源 | 医生 | academy/doctor/* |
| `ecg` 远程心电 | AI 诊断与会诊 | 医生 | doctor/ecg/* |
| `triage` 智慧急诊 | 急诊预检分诊入口 | 医生 | - |
| `selfcheck` 认证自评 | AI 模拟再认证 | 医生 | doctor/selfcheck |
| `ai` AI 助手 | 智能问答 | 医生 | doctor/kb/ask、ai/recognize |
| `mine` 我的 | 个人信息/密码/设置 | 医生 | doctor/password 等 |
| 分包 | 公告详情/通知/工单/个人资料/设置/关于/AI 模型/聊天 | 通用 | - |

### 2.2 核心功能业务流程

#### ① 登录 → 首页工作台（App 主入口）
```
登录（/cpx/auth/login，doctor 角色）→ onShow 并行拉取：
  ① doctor/stats → 5 项统计（今日新增/草稿/待审核/已通过/驳回）
  ② announcement/active → 公告轮播条（点击进公告详情页）
  ③ value-added/active → 增值服务大卡（swiper，点击跳转）
→ 8 宫格快捷入口（数据直报/数据分析/随访管理/救治医院/三会模板/胸痛学院/远程心电/智慧急诊）
```
- 数据流向：一次 onShow 并发 3 个接口；统计数字点击 → 跳 work 页自动筛选对应状态/日期
- 关键节点：公告/增值服务为 Web 端发布内容的"消费出口"；底部导航 3 Tab（首页/AI助手/我的）

#### ② 数据直报（核心业务：病例填报链路）
```
work 列表页：状态 Tab（全部/草稿/待审核/已通过/驳回）+ 日期范围 + 搜索 + 分页 + 下拉刷新
    │（首页统计点击可带 status/range 参数自动筛选）
    ▼
新建病例：doctor/case/create 患者快速建档（生成病例编号 CASE+日期+序号）
    ▼
模板表单填报：doctor/templates 取已发布模板字段 → 逐分类填写（基本信息/院前急救/急诊分诊/
   检验检查/院内诊疗/介入手术/患者转归）
    → doctor/case/{id}/save 保存草稿（可多次，整包 form_data 存 JSON）
    ▼
提交审核：doctor/case/{id}/submit（校验必填字段 + 时间链）
    → 状态 draft → submitted
    ▼
（驳回后）case/{id} 看审核反馈 → 修改 → 重新 submit（rejected → submitted）
```
- 数据流向：case_record（基础信息）+ case_detail.form_data（全部动态字段，MySQL JSON）
- 关键节点：**救治时间轴**（timeline）与**质控分析**（analysis）从 form_data 提取关键时间点
- 辅助：AI 图片识别（doctor/ai/recognize，通义千问 Vision）拍照提取患者信息自动填表

#### ③ 随访管理（审核通过后自动生成）
```
入口：首页 8 宫格 → 随访管理
列表：followup/groups 按患者聚合（计划 1/3/6/12 月，Tab：待随访/已完成/已过期）
执行：到期计划 → followup/{id}/submit 提交随访表单
    （记录：用药情况/危险因素控制/存活状态）
状态机：pending → submitted；到期未访 → overdue
```
- **关键节点（最新改造）**：审核员在 Web/App 通过病例后，**后端自动生成 1/3/6/12 月随访计划**（audit approve → 自动写 follow_up），App 随访页直接可见，无需手动触发

#### ④ 远程心电（AI 诊断 + 协同会诊）
```
ecg/upload 上传心电图（可选关联病例）→ AI 诊断（ai_diagnosis）
→ 记录列表（发起 + 接收合并）
→ 申请协同会诊：ecg/send-consult/{id} 选接收医院 → consult_sent
→ 接收方反馈：ecg/feedback/{id} → closed
状态机：draft → uploaded → consult_sent → received → closed
```

#### ⑤ 三会模板（PPT 生成）
```
meeting 页面 → 选会议类型（质量分析会 quality / 联合例会 joint / 典型病例讨论会 case）
→ 典型病例讨论会需先选病例 → 生成 PPT（meeting_record 记录文件）
```

#### ⑥ AI 助手 / 认证自评
```
ai 页：流式对话（qwen-plus）；知识库问答 kb/ask（回答标注来源文件+页码）；图片识别 ai/recognize
selfcheck：AI 模拟再认证自评
```

#### ⑦ 我的
```
个人信息/修改密码（doctor/password）/设置（主题/语言 zh·en）/退出登录
```

---

## 三、端间差异、重合与协同

### 3.1 功能矩阵（两端对比）

| 功能 | Web | App | 说明 |
|---|---|---|---|
| 登录认证 | ✅ admin/auditor | ✅ doctor | 共用 auth 接口，角色不同 |
| 病例填报 | ❌（仅测试 create） | ✅ 核心 | 医生移动端填报 |
| 病例查看 | ✅ 全量 | ✅ 仅本人 | 权限差异（admin 全库，doctor 本人） |
| 病例删除 | ✅ | ✅（仅本人） | Web 级联删全关联 |
| 模板管理 | ✅ **独有** | ✅ 只读（取已发布） | Web 配置，App 消费 |
| 审核操作 | ✅ **Web 独有**（工作台/待审/通过/驳回） | ❌ | 审核员在 Web 端处理，后端接口权限 ROLE_AUDITOR |
| 审核记录查看 | ✅ | ✅（病例内） | - |
| 随访管理 | ❌ | ✅ 执行 | 计划由审核通过自动生成 |
| 数据分析 | ✅ 全中心驾驶舱 | ✅ 个人 overview | 视角不同 |
| 医院/用户管理 | ✅ **独有** | ❌ | 后台管理 |
| 胸痛学院 | ✅ 上传管理 | ✅ 学习 | Web 发布 → App 学习 |
| 公告管理 | ✅ **独有** | ✅ 查看 | Web 发布 → App 首页轮播 |
| 增值服务 | ✅ **独有** | ✅ 查看跳转 | Web 配置 → App 展示 |
| 远程心电 | ❌ | ✅ | 医生端业务 |
| 三会 PPT | ❌ | ✅ | 医生端业务 |
| AI 助手 | ✅ 框架聊天 | ✅ 业务 AI | - |
| 系统日志 | ✅ | ❌ | 后台 |
| 后台管理（菜单/角色等） | ✅ 框架 | ❌ | 超管 |

### 3.2 权限差异（同一接口层，BusinessRole 隔离）

| 角色 | 可访问模块 |
|---|---|
| **admin** | stats、case 全量、template、hospital、user、academy 管理、announcement 管理、value_added 管理、log |
| **auditor** | audit（**Web 端审核操作**：工作台/待审/通过/驳回）、hospital/template 只读列表 |
| **doctor** | doctor/*（App 核心）、announcement/value_added/academy 只读 active 接口 |

> 实测：doctor 账号访问 Web 管理接口（如 announcement/list）→ **403**；审核员只能审核本医院病例。

### 3.3 数据互通与协同工作

```
                  Web 端（管理/配置/统计）
                    │  ① 配置模板 / 发布公告 / 配置增值服务 / 管理医院与账号
                    ▼
              ┌────────── MySQL 共享库 ──────────┐
              │   case_record / case_detail      │
              │   template / audit / follow_up   │
              │   announcement / value_added ... │
              └──────────────────────────────────┘
                    ▲              ▲
                    │              │
    App 医生端（填报/提交/随访）  Web 审核员（审核通过→自动生成随访）
```

**典型跨端协同链路**：
1. **配置流**：Web 建模板+发布 → App 按模板填报 → Web 驾驶舱看到数据增长
2. **业务流**：App 医生建档填报 → 提交 → **Web 端审核员通过** → **后端自动生成随访计划** → App 随访页执行
3. **内容流**：Web 发公告/增值服务/学院资源 → App 首页/入口实时展示
4. **治理流**：App 产生的数据 → Web 驾驶舱/统计/日志汇总 → 支撑运营决策

### 3.4 关键同步机制

| 机制 | 说明 |
|---|---|
| 实时数据库共享 | 无缓存中间层，App 提交 → Web 立即可见（如待审核数） |
| 模板发布生效 | App 填报时实时拉 `doctor/templates`，Web 发布新模板即刻可用 |
| 公告/增值服务 | App onShow 拉 `active` 接口（published/online 才返回），Web 发布即时生效 |
| 审核状态机 | 病例状态单向流转，两端读取同一 status |
| 统计实时性 | 驾驶舱/overview 每次请求实时聚合，无定时缓存 |

---

## 四、全链路流程速览（跨端）

```
┌─ Web：模板管理 ─┐   ┌─ Web：医院/用户管理 ─┐
│ 建模板+复制标准字段 │   │ 建医院/医生/审核员账号 │
│ 发布             │   └──────────┬─────────┘
└────────┬────────┘              │
         ▼                        ▼
  ┌────────────── App 医生端 ──────────────┐
  │ 登录 → 首页(统计/公告/增值服务) → 数据直报 │
  │  建档 → 模板表单填报 → 保存草稿 → 提交审核  │
  └──────────────────┬─────────────────────┘
                     ▼
          ┌── Web 审核员：待审列表 → 详情(时间链校验) ──┐
          │            通过 / 驳回                     │
          └──────┬──────────────────────────┬────────┘
                 ▼ (通过)                    ▼ (驳回)
       后端自动生成随访计划 1/3/6/12月       App 医生看反馈 → 修改 → 重新提交
                 ▼
          App 随访管理：到期执行 → 提交随访（用药/风险/存活）
                 ▼
       Web 驾驶舱 / 大屏：全中心数据汇总与质控展示
```

---

## 五、给开发/产品的一句话总结

> **Web 端 = 管理中枢**（模板、医院、账号、公告、增值服务、学院、统计、日志），**App 端 = 业务执行**（建档、填报、审核、随访、心电、三会、学习、AI）；两端共享同一 API 与 MySQL，靠 `BusinessRole` 三档权限隔离；病例状态机驱动全流程，模板驱动动态表单让数据结构免迁移，Web 发布的内容（公告/增值服务/学院）由 App 实时消费，App 产生的数据（病例/随访）实时回流 Web 驾驶舱与大屏。
