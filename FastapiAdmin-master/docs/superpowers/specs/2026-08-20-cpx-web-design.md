# 智慧胸痛中心智能数据填报系统 — Web 端设计文档

- 日期：2026-08-20
- 状态：已确认（待实施）
- 平台：FastapiAdmin v3.1.0（FastAPI + Vue3 + TS + MySQL + Redis）

## 1. 背景与目标

为胸痛中心数据填报系统构建 Web 端后台，面向两类角色：

- **管理员**：多医院管理、医院人员管理、病例数据管理、模板管理、统计、系统日志。
- **审核员**：审核工作台、待审核病例、病例审核、审核记录（仅限所属医院数据）。

Web 端与未来医生 APP 端共享同一套数据模型与登录体系。

## 2. 关键决策（已与用户确认）

| 决策点 | 结论 |
|------|------|
| 登录认证 | 基于 `user_account` 表独立登录，`role` 表区分角色（管理员/审核员），不使用 FastapiAdmin 的 sys_user 登录作为业务登录 |
| 表结构 | 保持现有 12 张业务表不变，模型直接映射；无软删除（物理删除），时间字段 `create_time/update_time` |
| 交付范围 | 两期：一期 = 登录/医院/用户/模板/病例/审核/日志；二期 = 驾驶舱/统计分析 |
| 冗余表 | 删除 `hospital1`、`hospital2` |

## 3. 现有数据模型（映射目标，保持不变）

| 表 | 关键字段 | 用途 |
|----|---------|------|
| `hospital` | hospital_name, hospital_level, province, city, address, contact_name, contact_phone, status(1正常/0禁用) | 医院 |
| `user_account` | username(唯一), password, real_name, phone, role_id(FK role), hospital_id(FK hospital), status, last_login_time | 用户（管理员/审核员/医生共用） |
| `role` | role_name, description | 角色（管理员/审核员/医生） |
| `doctor_info` | user_id, hospital_id, doctor_no(工号), department(科室), title(职称) | 医生扩展信息 |
| `auditor_info` | user_id, hospital_id, audit_level | 审核员扩展信息 |
| `case_record` | case_no(唯一), hospital_id, doctor_id, patient_name, gender, age, phone, status(draft/submitted/approved/rejected) | 病例主表 |
| `case_detail` | case_id, template_id, form_data(JSON) | 病例动态表单数据（模板驱动） |
| `audit_record` | case_id, auditor_id, audit_result(pass/reject), audit_comment, audit_time | 审核记录 |
| `report_template` | template_name, version, status, creator_id | 填报模板 |
| `template_field` | template_id, field_name, field_code, field_type, required_flag, sort_num | 模板字段 |
| `statistic_daily` | hospital_id, stat_date, case_count, audit_count, pass_count, reject_count | 每日统计（二期） |
| `system_log` | user_id, module, operation, description, ip_address | 业务操作日志 |

角色约定：`role.role_name` 取值 `管理员` / `审核员` / `医生`。医生账号给 APP 端使用，Web 端仅管理员/审核员登录。

## 4. 总体架构

采用方案 A：**复用 FastapiAdmin 前端外壳 + 独立业务登录 + 前端静态角色菜单**。

- 后端新增统一插件 `module_cpx`（URL 前缀 `/cpx`），承载全部业务模块；业务认证与框架 sys_user 认证完全隔离。
- 前端复用框架布局/组件；业务登录替换原登录页；菜单由 `builtinFrontendRoutes` 静态定义并按 `meta.roles` 过滤。
- FastapiAdmin 平台登录（admin/123456，sys_user）保留，用于平台级管理（可选）。

## 5. 后端设计

### 5.1 目录结构（自动注册，无需改 discover/init_app）

```
backend/app/plugin/module_cpx/
├── __init__.py
├── auth/          # 业务登录认证
│   ├── __init__.py
│   ├── model.py        # （无新表，用 user_account/role）
│   ├── schema.py
│   ├── crud.py
│   ├── service.py      # login/logout/userinfo/menus
│   ├── controller.py   # /cpx/auth/*
│   └── dependencies.py # get_current_business_user + BusinessRole
├── hospital/      # /cpx/hospital/*    医院 CRUD + 各医院医生/审核员/病例数
├── user/          # /cpx/user/*        医院人员（医生/审核员）管理
├── template/      # /cpx/template/*    模板 + 字段 CRUD
├── case/          # /cpx/case/*        病例列表/详情
├── audit/         # /cpx/audit/*       待审核/审核操作/记录/工作台统计
└── log/           # /cpx/log/*         系统日志查询
```

各实体沿用五文件模式：`model.py / schema.py / crud.py / service.py / controller.py`。

### 5.2 模型映射

- 模型继承 `MappedBase`（不继承 ModelMixin 的软删除字段），显式声明 `id / create_time / update_time` 及业务字段，精确映射现有表。
- `case_detail.form_data` 为 `JSON` 列；模板字段用 `field_code` 作为 JSON key。
- CRUD 基类 `CRUDBase` 对无 `is_deleted` 的表自动走物理删除（框架已支持）。

### 5.3 业务认证（auth 模块）

- **登录** `POST /cpx/auth/login`：校验 user_account 存在、密码（`PwdUtil.verify_password`）、status 正常、role 为管理员或审核员；审核员（及所属医院被禁用时）额外校验 `hospital.status=1`（医院禁用后其用户禁止登录）→ 生成 JWT（复用 `create_access_token`，sub=session_id）→ 写 Redis `cpx_session:{session_id}`（内容：user_id、user_name、role、role_name、hospital_id、hospital_name）→ 返回 `{access_token, userinfo}`。
- **登出** `POST /cpx/auth/logout`：删 Redis session。
- **用户信息** `GET /cpx/auth/userinfo`：返回 id/username/real_name/phone/role/role_name/hospital_id/hospital_name/is_superuser=false，附带角色码供前端过滤菜单（`role_code`：admin / auditor）。
- **依赖** `get_current_business_user`：解析 Bearer JWT → Redis `cpx_session` → 加载 user_account（校验 status）→ 返回业务上下文（含 role、hospital）。
- **角色校验依赖** `BusinessRole(["admin"])` / `["auditor"]`：与框架 `AuthPermission` 同构，按角色码校验；管理员全量，审核员仅限自身医院 + 审核相关接口。
- **数据隔离**：审核员接口在 service 层强制 `hospital_id == 当前用户 hospital_id`；管理员不限制。
- 密码哈希：复用 `PwdUtil`（PBKDF2-sha256）。注意 DB 现有数据为空，新建账号统一哈希。

### 5.4 业务接口清单（一期）

**auth** `/cpx/auth`
- POST `/login` 登录；POST `/logout` 登出；GET `/userinfo` 用户信息；GET `/menus` 角色菜单（可选，前端静态则不需要）

**hospital** `/cpx/hospital`
- GET `/list` 分页（含 doctor_count/auditor_count/case_count 计数）
- GET `/detail/{id}`；POST `/create`；PUT `/update/{id}`；PATCH `/status/batch`（禁用/启用）
- GET `/all` 下拉选项（供用户管理/病例筛选用）

**user** `/cpx/user`
- GET `/doctors` 按 hospital_id 分页查询医生（关联 doctor_info）
- GET `/auditors` 按 hospital_id 分页查询审核员（关联 auditor_info）
- POST `/doctor` 新增医生（事务：user_account + doctor_info；role=医生；默认密码）
- POST `/auditor` 新增审核员（user_account + auditor_info；role=审核员）
- PUT `/update/{id}` 修改；PATCH `/status/batch` 禁用/启用；PUT `/password/{id}` 重置密码
- GET `/detail/{id}`

**template** `/cpx/template`
- GET `/list` 模板分页；POST `/create`；PUT `/update/{id}`；PUT `/publish/{id}` 发布（state=1）
- GET `/detail/{id}`（含字段列表）；POST `/fields` 添加字段；PUT `/field/{id}` 修改字段；DELETE `/field/{id}` 删除字段

**case** `/cpx/case`
- GET `/list` 分页筛选（hospital_id/doctor_id/status/时间范围）；GET `/detail/{id}`（主表 + case_detail.form_data 解析 + 最新审核记录）
- 注：病例创建/提交由医生 APP 端负责，一期仅 Web 端只读 + 状态筛选；为联调提供可选的 POST `/create` 测试入口

**audit** `/cpx/audit`
- GET `/workbench` 统计卡（待审核/今日审核/通过/驳回数）
- GET `/pending` 待审核病例分页（status=submitted，限本院）
- GET `/history` 审核记录分页
- GET `/detail/{case_id}` 审核详情（病例 + form_data 渲染 + 校验提示）
- POST `/approve` 审核通过（status→approved + 写 audit_record）
- POST `/reject` 审核驳回（status→rejected + 必填驳回原因 + 写 audit_record）
- 校验：必填字段完整性（template_field.required_flag）、时间逻辑（发病时间 ≤ 到院时间 ≤ 首份心电图时间 ≤ PCI时间）

**log** `/cpx/log`
- GET `/list` 分页筛选（user_id/module/时间范围）

### 5.5 业务操作日志

- 通过业务 service 层统一调用 `LogService.create(...)` 记录，字段：user_id/module/operation/description/ip_address（IP 从 Request 取）。
- 覆盖：医院增删改、用户增删改/重置密码、模板增改发、审核通过/驳回等。

### 5.6 错误处理

- 统一抛出框架 `CustomException`（消息+code+status_code），由框架全局异常处理器返回 `{code,msg,data}`。
- 常见错误：账号不存在/密码错误/账号禁用（401）、无权限（403）、医院已禁用登录拒绝、重复登录账号（唯一键冲突）。

## 6. 前端设计

### 6.1 认证与登录

- 新建业务登录页 `src/views/cpx/login/index.vue`，替换 `src/router/routes.ts` 中的 LoginView 引用。
- `src/store/modules/user.store.ts` 新增业务登录 action（或新建 `src/store/modules/cpx.store.ts`）：调用 `/cpx/auth/login` → 存 token → 拉 userinfo（含 role_code）→ 存 info。
- `src/api/cpx/auth.ts`：登录/登出/用户信息。
- 前端访问控制沿用框架 `Auth` 工具（token 存 localStorage），`Auth.isLoggedIn()` 判断登录态。

### 6.2 菜单与路由（静态角色菜单）

- 在 `src/router/MenuProcessor.ts` 的 `builtinFrontendRoutes` 中定义业务菜单树（AppRouteRecord 结构），根节点 `meta.roles: ["admin"]` 或 `["auditor"]`。
- **保持 `VITE_ACCESS_MODE = mixed`**（不改配置）。`MenuProcessor.processMixedMenu` 在业务用户场景下自然降级：守卫跳过 `getUserInfo()` → `routeList` 为空 → 后端菜单部分为空 → 仅挂载 `builtinFrontendRoutes`。
- `src/router/guards.ts`：为业务登录用户加分支——跳过框架 `getUserInfo()`（该接口依赖 sys_user，业务用户会失败），直接以 `builtinFrontendRoutes` 注册路由；平台管理员（sys_user）仍走原框架流程，可同时看到系统管理与业务菜单。
- 首页 `/home`、登录页等壳层路由保持静态；业务首页 `HOME_PAGE_PATH` 视情况调整（如 `/home` 改为业务驾驶舱占位）。

### 6.3 页面（一期）

```
src/views/cpx/
├── login/index.vue            # 业务登录页
├── hospital/index.vue         # 医院管理列表/新增/编辑/禁用
├── hospital-user/index.vue    # 医院人员管理（选医院 → 审核员/医生 Tab）
├── template/index.vue         # 模板列表 + 字段管理
├── case/index.vue             # 病例列表/筛选/详情
├── audit/
│   ├── workbench.vue          # 审核工作台统计卡
│   ├── pending.vue            # 待审核列表
│   ├── audit.vue              # 病例审核（表单渲染 + 校验 + 通过/驳回）
│   └── history.vue            # 审核记录
└── system-log/index.vue       # 系统日志
```

### 6.4 复用组件

- FaTable / FaTableHeader / FaTableHeaderLeft / FaSearchBar / FaForm / FaDialog / FaDescriptions / FaStatusTag / FaStatsCard / FaPagination。
- 动态表单渲染：按 template_field 的 field_type（文本→ElInput、数字→ElInputNumber、日期→ElDatePicker、时间→ElTimePicker、选择→ElSelect）动态渲染，数据存 JSON。
- 图表（二期）：FaLineChart / FaBarChart / FaRingChart。

### 6.5 API 层

`src/api/cpx/{auth,hospital,user,template,case,audit,log}.ts`，沿用 `request` 封装与 `ApiResponse/PageResult` 全局类型。

## 7. 一期种子数据

后端首次启动后手动初始化（或写初始化脚本）：
- `role`：`管理员`、`审核员`、`医生`
- `user_account`：管理员账号（如 `admin` / `Admin123`，role=管理员）
- 可选演示医院若干
- **新建医生/审核员的默认初始密码**：`Aa123456`（满足 PwdUtil 强度要求），用户可后台重置

## 8. 测试与验收

- 后端：Swagger（/docs）逐接口验证；权限/数据隔离用例。
- 前端：登录（管理员/审核员不同菜单）、医院 CRUD、人员管理、模板字段、病例详情、审核通过/驳回全流程、日志查询。
- 验收标准：一期 8 个模块可用；审核员只能看到本医院病例；审核通过/驳回正确流转状态并留痕。

## 9. 二期规划（暂不实施）

- 数据驾驶舱：医院/用户/病例/审核统计卡 + 病例趋势图 + 医院病例排行 + 审核率图表（`statistic_daily` 或实时聚合）。
- 统计分析：病例/医院/质量（数据完整率、缺失字段、异常数据）/审核统计。

## 10. 表归属冲突处理（重要）

现有示例插件 `module_user_account`、`module_role` 已把 `user_account`、`role` 表映射进 SQLAlchemy metadata；`module_cpx` 也要映射这两张表，**同一 metadata 不允许同名表重复映射，否则启动报错**。

处理方案（已确认）：
- **移除这两个示例插件**（后端 `backend/app/plugin/module_user_account/`、`module_role/`，前端 `src/views/module_user_account/`、`module_role/`）。它们是模板示例，模型与真实表结构不符（created_time vs create_time），且 user/role 管理已由 `module_cpx` 重新实现。**2026-08-20 用户已确认删除。**

## 11. 明确不做的（本期）

- 医生 APP 端（仅预留 user_account 角色=医生 及 doctor_info 数据支撑）
- FastapiAdmin 系统管理模块的深度整合（平台管理仍走 admin/123456，可选）
- 软删除、审计字段改造
