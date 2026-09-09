# 智慧胸痛管理 · OpenAPI 接口文档

> 本文档由生产环境真实 OpenAPI Schema 自动生成（快照），可用于接口联调与开发参考。
>
> - **系统**：智慧胸痛中心管理系统（胸痛中心数据填报、审核与质控一体化管理平台）
> - **Schema 版本**：3.0.0（OpenAPI 3.1.0）
> - **接口规模**：350 个操作 / 337 个路径 / 42 个模块 / 291 个数据模型
> - **导出时间**：2026-09-08（生产 106.55.33.111 导出）
> - **鉴权方式**：登录后携带 Token（Authorization Bearer / 请求头），未授权返回 401

---

## 目录（模块索引）

| 模块 | 接口数 | 模块 | 接口数 |
|---|---|---|---|
| 医生端 | 37 | 定时任务管理 | 16 |
| 用户管理 | 15 | 字典管理 | 14 |
| 动态模板管理 | 14 | 系统聊天 | 12 |
| 代码生成 | 12 | 病例管理 | 12 |
| AI管理 | 11 | 资源管理 | 9 |
| 认证授权 | 9 | 角色管理 | 9 |
| 工单管理 | 9 | 定时任务节点管理 | 9 |
| 胸痛学院 | 9 | 公告管理 | 9 |
| 医院用户管理 | 9 | 示例管理 | 9 |
| 岗位管理 | 8 | 存储源管理 | 8 |
| 增值服务管理 | 8 | 缓存监控 | 7 |
| 日志管理 | 7 | 公告通知 | 7 |
| 版本管理 | 7 | 流程编排 | 7 |
| 工作流节点 | 7 | 病例审核 | 7 |
| 部门管理 | 6 | 菜单管理 | 6 |
| 存储文件 | 6 | 文件传输 | 6 |
| 医院管理 | 6 | 在线用户 | 5 |
| 健康检查 | 4 | 业务登录认证 | 3 |
| 文件管理 | 2 | 参数管理 | 2 |
| AI知识库 | 2 | 系统日志 | 2 |
| 数据统计 | 2 | 服务器监控 | 1 |

---

## 医生端（37 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/doctor/case/{id}` | 删除我的病例（仅本人，级联删除关联数据） | id(path) | — | 200 |
| `DELETE` | `/cpx/doctor/meeting/{id}` | 删除生成记录 | id(path) | — | 200 |
| `GET` | `/cpx/doctor/stats` | 医生工作台统计 | — | — | 200 |
| `GET` | `/cpx/doctor/me` | 当前医生基本信息 | — | — | 200 |
| `GET` | `/cpx/doctor/templates` | 已发布模板列表（含字段） | — | — | 200 |
| `GET` | `/cpx/doctor/case/{id}` | 病例详情（含审核反馈） | id(path) | — | 200 |
| `GET` | `/cpx/doctor/case/list` | 我的病例列表 | — | — | 200 |
| `GET` | `/cpx/doctor/field-dict` | 胸痛标准字段字典 | — | — | 200 |
| `GET` | `/cpx/doctor/case/{id}/timeline` | 救治时间轴（含关键指标） | id(path) | — | 200 |
| `GET` | `/cpx/doctor/case/{id}/analysis` | 单病例质控分析 | id(path) | — | 200 |
| `GET` | `/cpx/doctor/followup/list` | 我的随访列表 | — | — | 200 |
| `GET` | `/cpx/doctor/followup/groups` | 随访按患者聚合列表 | — | — | 200 |
| `GET` | `/cpx/doctor/followup/{id}` | 随访单条详情（含患者上下文） | id(path) | — | 200 |
| `GET` | `/cpx/doctor/stats/overview` | 数据概览（累计/诊断分布/趋势） | — | — | 200 |
| `GET` | `/cpx/doctor/units` | 救治医院列表 | — | — | 200 |
| `GET` | `/cpx/doctor/ecg/list` | 远程心电记录列表（发起+接收合并） | — | — | 200 |
| `GET` | `/cpx/doctor/ecg/list-by-case/{case_id}` | 某病例心电记录列表（供随访心电图联动） | case_id(path) | — | 200 |
| `GET` | `/cpx/doctor/ecg/detail/{id}` | 远程心电详情 | id(path) | — | 200 |
| `GET` | `/cpx/doctor/selfcheck` | AI 模拟再认证自评 | — | — | 200 |
| `GET` | `/cpx/doctor/meeting/templates` | 三会模板列表 | — | — | 200 |
| `GET` | `/cpx/doctor/meeting/list` | 三会 PPT 生成记录 | — | — | 200 |
| `GET` | `/cpx/doctor/meeting/{id}` | 会议内容预览 | id(path) | — | 200 |
| `POST` | `/cpx/doctor/case/create` | 患者快速建档（生成病例编号） | — | app__plugin__module_cpx__doctor__schema__CaseCreateSchema | 200 |
| `POST` | `/cpx/doctor/case/{id}/save` | 保存病例表单（草稿） | id(path) | FormSaveSchema | 200 |
| `POST` | `/cpx/doctor/case/{id}/submit` | 提交病例审核 | id(path) | — | 200 |
| `POST` | `/cpx/doctor/password` | 修改登录密码 | — | PasswordChangeSchema | 200 |
| `POST` | `/cpx/doctor/followup/generate` | 为已通过病例生成随访计划 | — | — | 200 |
| `POST` | `/cpx/doctor/followup/{id}/submit` | 提交随访表单 | id(path) | FollowUpSubmitSchema | 200 |
| `POST` | `/cpx/doctor/ecg/upload` | 远程心电上传（AI 诊断 + 病例快照） | — | — | 200 |
| `POST` | `/cpx/doctor/ecg/send-consult/{id}` | 申请协同会诊（选接收医院） | id(path) | (自由对象) | 200 |
| `POST` | `/cpx/doctor/ecg/feedback/{id}` | 接收方医生写反馈（结束会诊） | id(path) | (自由对象) | 200 |
| `POST` | `/cpx/doctor/kb/ask` | 认证知识库 AI 问答（医生端，回答标注来源文件与页码） | — | (自由对象) | 200 |
| `POST` | `/cpx/doctor/ai/recognize` | AI 图片/文字识别：通义千问 Vision / 文字解析提取患者信息 | — | (自由对象) | 200 |
| `POST` | `/cpx/doctor/ai/asr` | AI 语音识别（智谱 GLM-ASR-2512 音频转写） | — | (自由对象) | 200 |
| `POST` | `/cpx/doctor/meeting/generate` | 生成三会 PPT | — | — | 200 |
| `POST` | `/cpx/doctor/upload/image` | 上传图片（病历/心电图等） | — | — | 200 |
| `PUT` | `/cpx/doctor/case/{id}` | 更新患者基础信息 | id(path) | app__plugin__module_cpx__doctor__schema__CaseUpdateSchema | 200 |

## 定时任务管理（16 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/task/cronjob/job/scheduler/jobs/clear` | 清空所有任务 | — | — | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/task/cronjob/job/task/remove/{job_id}` | 移除任务 | job_id(path) | — | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/task/cronjob/job/log/delete` | 删除执行日志 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/task/cronjob/job/scheduler/status` | 获取调度器状态 | — | — | 200 ResponseSchema_dict_ |
| `GET` | `/task/cronjob/job/scheduler/jobs` | 获取调度器任务列表 | — | — | 200 ResponseSchema_list_dict__ |
| `GET` | `/task/cronjob/job/scheduler/console` | 获取调度器控制台信息 | — | — | 200 ResponseSchema_str_ |
| `GET` | `/task/cronjob/job/log/list` | 查询执行日志列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_JobOutSchema__ |
| `GET` | `/task/cronjob/job/log/detail/{id}` | 获取执行日志详情 | id(path) | — | 200 ResponseSchema_JobOutSchema_ |
| `POST` | `/task/cronjob/job/scheduler/start` | 启动调度器 | — | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/scheduler/pause` | 暂停调度器 | — | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/scheduler/resume` | 恢复调度器 | — | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/scheduler/shutdown` | 关闭调度器 | — | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/task/pause/{job_id}` | 暂停任务 | job_id(path) | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/task/resume/{job_id}` | 恢复任务 | job_id(path) | — | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/job/task/run/{job_id}` | 立即执行任务 | job_id(path) | — | 200 ResponseSchema_NoneType_ |
| `PUT` | `/task/cronjob/job/task/modify/{job_id}` | 修改任务 | job_id(path) | (自由对象) | 200 ResponseSchema_NoneType_ |

## 用户管理（15 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/user/delete` | 删除用户 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/user/current/info` | 查询当前用户信息 | — | — | 200 ResponseSchema_CurrentUserOutSchema_ |
| `GET` | `/system/user/list` | 查询用户 | search(query) | — | 200 ResponseSchema_PageResultSchema_UserOutSchema__ |
| `GET` | `/system/user/detail/{id}` | 查询用户详情 | id(path) | — | 200 ResponseSchema_UserOutSchema_ |
| `GET` | `/system/user/import/template` | 获取用户导入模板 | — | — | 200 |
| `PATCH` | `/system/user/status/batch` | 批量修改用户状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/user/password/forget` | 忘记密码 | — | UserForgetPasswordSchema | 200 ResponseSchema_UserOutSchema_ |
| `POST` | `/system/user/register` | 用户注册 | — | UserRegisterSchema | 200 ResponseSchema_UserOutSchema_ |
| `POST` | `/system/user/create` | 创建用户 | — | UserCreateSchema | 201 ResponseSchema_UserOutSchema_ |
| `POST` | `/system/user/export` | 导出用户 | — | UserQueryParam | 200 |
| `POST` | `/system/user/import/data` | 导入用户 | — | — | 200 ResponseSchema_NoneType_ |
| `PUT` | `/system/user/current/info/update` | 更新当前用户基本信息 | — | CurrentUserUpdateSchema | 200 ResponseSchema_UserOutSchema_ |
| `PUT` | `/system/user/password/change` | 修改当前用户密码 | — | UserChangePasswordSchema | 200 ResponseSchema_UserOutSchema_ |
| `PUT` | `/system/user/password/reset/{id}` | 重置用户密码 | id(path) | app__api__v1__module_system__user__schema__ResetPasswordSchema | 200 ResponseSchema_UserOutSchema_ |
| `PUT` | `/system/user/update/{id}` | 修改用户 | id(path) | UserUpdateSchema | 200 ResponseSchema_UserOutSchema_ |

## 字典管理（14 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/dict/type/delete` | 删除字典类型 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/system/dict/data/delete` | 删除字典数据 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/dict/type/detail/{id}` | 获取字典类型详情 | id(path) | — | 200 ResponseSchema_DictTypeOutSchema_ |
| `GET` | `/system/dict/type/list` | 查询字典类型 | search(query) | — | 200 ResponseSchema_PageResultSchema_DictTypeOutSchema__ |
| `GET` | `/system/dict/type/optionselect` | 获取全部字典类型 | — | — | 200 ResponseSchema_list_DictTypeOutSchema__ |
| `GET` | `/system/dict/data/detail/{id}` | 获取字典数据详情 | id(path) | — | 200 ResponseSchema_DictDataOutSchema_ |
| `GET` | `/system/dict/data/list` | 查询字典数据 | search(query) | — | 200 ResponseSchema_PageResultSchema_DictDataOutSchema__ |
| `GET` | `/system/dict/data/info/{dict_type}` | 根据字典类型获取数据 | dict_type(path) | — | 200 ResponseSchema_list_DictDataOutSchema__ |
| `PATCH` | `/system/dict/type/status/batch` | 批量修改字典类型状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `PATCH` | `/system/dict/data/status/batch` | 批量修改字典数据状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/dict/type/create` | 创建字典类型 | — | DictTypeCreateSchema | 201 ResponseSchema_DictTypeOutSchema_ |
| `POST` | `/system/dict/data/create` | 创建字典数据 | — | DictDataCreateSchema | 201 ResponseSchema_DictDataOutSchema_ |
| `PUT` | `/system/dict/type/update/{id}` | 修改字典类型 | id(path) | DictTypeUpdateSchema | 200 ResponseSchema_DictTypeOutSchema_ |
| `PUT` | `/system/dict/data/update/{id}` | 修改字典数据 | id(path) | DictDataUpdateSchema | 200 ResponseSchema_DictDataOutSchema_ |

## 动态模板管理（14 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/template/field/{id}` | 删除模板字段 | id(path) | — | 200 |
| `DELETE` | `/cpx/template/{id}` | 删除模板（未被病例使用时允许） | id(path) | — | 200 |
| `GET` | `/cpx/template/list` | 分页查询模板 | — | — | 200 |
| `GET` | `/cpx/template/all` | 全部启用模板（下拉选项） | — | — | 200 |
| `GET` | `/cpx/template/detail/{id}` | 获取模板详情（含字段） | id(path) | — | 200 |
| `POST` | `/cpx/template/create` | 新增模板 | — | TemplateCreateSchema | 200 |
| `POST` | `/cpx/template/fields` | 添加模板字段 | — | TemplateFieldCreateSchema | 200 |
| `POST` | `/cpx/template/copy-standard/{template_id}` | 复制标准模板（覆盖现有字段） | template_id(path) | — | 200 |
| `POST` | `/cpx/template/tab-rename` | 重命名模板内某分类（批量更新） | — | (自由对象) | 200 |
| `POST` | `/cpx/template/tab-delete` | 删除模板内某分类及其所有字段 | — | (自由对象) | 200 |
| `PUT` | `/cpx/template/update/{id}` | 修改模板 | id(path) | TemplateUpdateSchema | 200 |
| `PUT` | `/cpx/template/publish/{id}` | 发布模板 | id(path) | — | 200 |
| `PUT` | `/cpx/template/unpublish/{id}` | 取消发布（仅未被病例使用时允许） | id(path) | — | 200 |
| `PUT` | `/cpx/template/field/{id}` | 修改模板字段 | id(path) | TemplateFieldUpdateSchema | 200 |

## 系统聊天（12 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/chat/groups/{group_id}` | 解散群组 | group_id(path) | — | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/system/chat/groups/{group_id}/members` | 移除成员 | group_id(path) | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/chat/conversations` | 会话列表 | — | — | 200 ResponseSchema_list_ |
| `GET` | `/system/chat/messages` | 历史消息 | — | — | 200 ResponseSchema_dict_ |
| `GET` | `/system/chat/users` | 用户选择器 | — | — | 200 ResponseSchema_list_ |
| `GET` | `/system/chat/groups/{group_id}` | 群组详情 | group_id(path) | — | 200 ResponseSchema_dict_ |
| `POST` | `/system/chat/messages` | 发送消息 | — | ChatMessageCreateSchema | 200 ResponseSchema_dict_ |
| `POST` | `/system/chat/read` | 标记已读 | — | ChatReadSchema | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/chat/groups` | 创建群组 | — | ChatGroupCreateSchema | 200 ResponseSchema_dict_ |
| `POST` | `/system/chat/groups/{group_id}/members` | 添加成员 | group_id(path) | ChatGroupMemberSchema | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/chat/groups/{group_id}/quit` | 退出群组 | group_id(path) | — | 200 ResponseSchema_NoneType_ |
| `PUT` | `/system/chat/groups/{group_id}` | 修改群组 | group_id(path) | ChatGroupUpdateSchema | 200 ResponseSchema_NoneType_ |

## 代码生成（12 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/generator/gencode/delete` | 删除业务表信息 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/generator/gencode/list` | 查询代码生成业务表列表 | search(query) | — | 200 ResponseSchema_list_GenTableOutSchema__ |
| `GET` | `/generator/gencode/db/list` | 查询数据库表列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_GenDBTableSchema__ |
| `GET` | `/generator/gencode/detail/{table_id}` | 获取业务表详细信息 | table_id(path) | — | 200 ResponseSchema_GenTableOutSchema_ |
| `GET` | `/generator/gencode/preview/{table_id}` | 预览代码 | table_id(path) | — | 200 ResponseSchema_GenTableOutSchema_ |
| `GET` | `/generator/gencode/sync_db/preview/{table_name}` | 同步数据库差异预览 | table_name(path) | — | 200 ResponseSchema_GenSyncPreviewSchema_ |
| `PATCH` | `/generator/gencode/batch/output` | 批量生成代码 | — | (自由对象) | 200 |
| `POST` | `/generator/gencode/import` | 导入表结构 | — | (自由对象) | 200 ResponseSchema_bool_ |
| `POST` | `/generator/gencode/create` | 创建表结构 | — | GenCreateTableSqlBody | 201 ResponseSchema_bool_ |
| `POST` | `/generator/gencode/output/{table_name}` | 生成代码到指定路径 | table_name(path) | — | 200 ResponseSchema_bool_ |
| `POST` | `/generator/gencode/sync_db/{table_name}` | 同步数据库 | table_name(path) | — | 200 ResponseSchema_NoneType_ |
| `PUT` | `/generator/gencode/update/{table_id}` | 编辑业务表信息 | table_id(path) | GenTableSchema | 200 ResponseSchema_GenTableOutSchema_ |

## 病例管理（12 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/case/{id}` | 删除病例（级联删除详情/审核/随访/心电） | id(path) | — | 200 |
| `GET` | `/cpx/case/list` | 分页查询病例 | — | — | 200 |
| `GET` | `/cpx/case/export` | 导出病例数据 Excel | — | — | 200 |
| `GET` | `/cpx/case/export_pdf` | 导出病例数据 PDF | — | — | 200 |
| `GET` | `/cpx/case/export_pdf/{id}` | 导出单个病例报告 PDF | id(path) | — | 200 |
| `GET` | `/cpx/case/detail/{id}` | 获取病例详情 | id(path) | — | 200 |
| `GET` | `/cpx/case/timeline/{id}` | 救治时间轴（含关键质控指标） | id(path) | — | 200 |
| `GET` | `/cpx/case/analysis/{id}` | 单病例分析（质控指标校验） | id(path) | — | 200 |
| `GET` | `/cpx/case/followup/{id}` | 病例随访记录详情 | id(path) | — | 200 |
| `POST` | `/cpx/case/create` | 新增病例（测试/联调） | — | app__plugin__module_cpx__case__schema__CaseCreateSchema | 200 |
| `POST` | `/cpx/case/submit/{id}` | 提交病例（草稿/驳回 → 待审核） | id(path) | — | 200 |
| `PUT` | `/cpx/case/{id}` | 更新病例基础信息（web 与 APP 互通） | id(path) | app__plugin__module_cpx__case__schema__CaseUpdateSchema | 200 |

## AI管理（11 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/ai/chat/delete` | 删除会话 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/ai/chat/model/{config_id}` | 删除指定 ID 的 AI 模型配置 | config_id(path) | — | 200 ResponseSchema_NoneType_ |
| `GET` | `/ai/chat/detail/{session_id}` | 获取会话详情 | session_id(path) | — | 200 ResponseSchema_dict_str__Any__ |
| `GET` | `/ai/chat/list` | 查询会话列表 | search(query) | — | 200 ResponseSchema_dict_ |
| `GET` | `/ai/chat/model` | 获取 AI 模型配置列表 | — | — | 200 ResponseSchema_AiModelConfigListResponse_ |
| `POST` | `/ai/chat/create` | 创建会话 | — | ChatSessionCreateSchema | 201 ResponseSchema_dict_str__Any__ |
| `POST` | `/ai/chat/ai-chat` | AI 对话（非流式） | — | AiChatRequestSchema | 200 ResponseSchema_AiChatResponseSchema_ |
| `POST` | `/ai/chat/model` | 新增一个 AI 模型配置 | — | AiModelConfigUpdateSchema | 201 ResponseSchema_dict_str__Any__ |
| `POST` | `/ai/chat/model/{config_id}/activate` | 切换激活的 AI 模型配置 | config_id(path) | — | 200 ResponseSchema_NoneType_ |
| `PUT` | `/ai/chat/update/{session_id}` | 更新会话 | session_id(path) | ChatSessionUpdateSchema | 200 ResponseSchema_NoneType_ |
| `PUT` | `/ai/chat/model/{config_id}` | 更新指定 ID 的 AI 模型配置 | config_id(path) | AiModelConfigUpdateSchema | 200 ResponseSchema_dict_str__Any__ |

## 资源管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/monitor/resource/delete` | 删除文件 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/monitor/resource/list` | 获取目录列表 | search(query) | — | 200 ResponseSchema_list_ResourceItemSchema__ |
| `GET` | `/monitor/resource/download` | 下载文件 | path(query) | — | 200 |
| `POST` | `/monitor/resource/upload` | 上传文件 | — | — | 200 ResponseSchema_UploadResponseSchema_ |
| `POST` | `/monitor/resource/move` | 移动文件 | — | ResourceMoveSchema | 200 ResponseSchema_NoneType_ |
| `POST` | `/monitor/resource/copy` | 复制文件 | — | ResourceCopySchema | 200 ResponseSchema_NoneType_ |
| `POST` | `/monitor/resource/rename` | 重命名文件 | — | ResourceRenameSchema | 200 ResponseSchema_NoneType_ |
| `POST` | `/monitor/resource/mkdir` | 创建目录 | — | ResourceCreateDirSchema | 201 ResponseSchema_NoneType_ |
| `POST` | `/monitor/resource/export` | 导出资源列表 | — | — | 200 |

## 认证授权（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/system/auth/captcha/get` | 获取验证码 | — | — | 200 ResponseSchema_CaptchaOutSchema_ |
| `GET` | `/system/auth/oauth/{provider}/login` | 第三方OAuth跳转 | provider(path) | — | 200 |
| `POST` | `/system/auth/login` | 登录 | — | — | 200 LoginOutSchema |
| `POST` | `/system/auth/token/refresh` | 刷新token | — | (自由对象) | 200 ResponseSchema_JWTOutSchema_ |
| `POST` | `/system/auth/captcha/slider/complete` | 滑块验证完成 | — | SliderCompleteSchema | 200 ResponseSchema_SliderCompleteOutSchema_ |
| `POST` | `/system/auth/logout` | 退出登录 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/auth/wx-login` | 微信小程序登录 | — | WxLoginSchema | 200 ResponseSchema_LoginOutSchema_ |
| `POST` | `/system/auth/wx-phone-login` | 微信小程序手机号登录 | — | WxPhoneLoginSchema | 200 ResponseSchema_LoginOutSchema_ |
| `POST` | `/system/auth/wx-qrcode/generate` | 生成小程序码 | — | WxQrCodeSchema | 200 ResponseSchema_WxQrCodeOutSchema_ |

## 角色管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/role/delete` | 删除角色 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/role/list` | 查询角色 | search(query) | — | 200 ResponseSchema_PageResultSchema_RoleOutSchema__ |
| `GET` | `/system/role/detail/{id}` | 查询角色详情 | id(path) | — | 200 ResponseSchema_RoleOutSchema_ |
| `GET` | `/system/role/options` | 获取角色下拉选项 | — | — | 200 ResponseSchema_list_dict_str__Union_int__str____ |
| `PATCH` | `/system/role/status/batch` | 批量修改角色状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/role/create` | 创建角色 | — | RoleCreateSchema | 201 ResponseSchema_RoleOutSchema_ |
| `POST` | `/system/role/export` | 导出角色 | — | RoleQueryParam | 200 |
| `PUT` | `/system/role/update/{id}` | 修改角色 | id(path) | RoleUpdateSchema | 200 ResponseSchema_RoleOutSchema_ |
| `PUT` | `/system/role/permission` | 角色授权 | — | RolePermissionSettingSchema | 200 ResponseSchema_NoneType_ |

## 工单管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/ticket/delete` | 删除工单 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/ticket/list` | 工单列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_TicketOutSchema__ |
| `GET` | `/system/ticket/detail/{id}` | 获取工单详情 | id(path) | — | 200 ResponseSchema_TicketOutSchema_ |
| `GET` | `/system/ticket/{ticket_id}/comments` | 工单评论列表 | ticket_id(path) | — | 200 ResponseSchema_PageResultSchema_TicketCommentOutSchema__ |
| `POST` | `/system/ticket/create` | 创建工单 | — | TicketCreateSchema | 201 ResponseSchema_TicketOutSchema_ |
| `POST` | `/system/ticket/export` | 导出工单 | — | TicketQueryParam | 200 |
| `POST` | `/system/ticket/{ticket_id}/comments` | 创建评论 | ticket_id(path) | TicketCommentCreateSchema | 201 ResponseSchema_TicketCommentOutSchema_ |
| `PUT` | `/system/ticket/update/{id}` | 更新工单 | id(path) | TicketUpdateSchema | 200 ResponseSchema_TicketOutSchema_ |
| `PUT` | `/system/ticket/batch` | 批量更新工单 | — | TicketBatchSchema | 200 ResponseSchema |

## 定时任务节点管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/task/cronjob/node/delete` | 删除节点 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/task/cronjob/node/clear` | 清空节点 | — | — | 200 ResponseSchema_NoneType_ |
| `GET` | `/task/cronjob/node/options` | 获取定时任务节点列表 | — | — | 200 ResponseSchema_list_dict__ |
| `GET` | `/task/cronjob/node/detail/{id}` | 获取节点详情 | id(path) | — | 200 ResponseSchema_NodeOutSchema_ |
| `GET` | `/task/cronjob/node/list` | 查询节点 | search(query) | — | 200 ResponseSchema_PageResultSchema_NodeOutSchema__ |
| `PATCH` | `/task/cronjob/node/status/batch` | 批量设置节点状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/task/cronjob/node/create` | 创建节点 | — | NodeCreateSchema | 201 ResponseSchema_NodeOutSchema_ |
| `POST` | `/task/cronjob/node/execute/{id}` | 调试节点 | id(path) | NodeExecuteSchema | 200 ResponseSchema_dict_ |
| `PUT` | `/task/cronjob/node/update/{id}` | 修改节点 | id(path) | NodeUpdateSchema | 200 ResponseSchema_NodeOutSchema_ |

## 胸痛学院（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/academy/{id}` | 删除学院内容 | id(path) | — | 200 |
| `GET` | `/cpx/academy/list` | 分页查询学院内容 | — | — | 200 |
| `GET` | `/cpx/academy/detail/{id}` | 学院内容详情 | id(path) | — | 200 |
| `GET` | `/cpx/academy/doctor/list` | 医生端：已发布学院内容列表 | — | — | 200 |
| `GET` | `/cpx/academy/doctor/detail/{id}` | 医生端：学院内容详情（浏览量+1） | id(path) | — | 200 |
| `POST` | `/cpx/academy/create` | 新增学院内容 | — | AcademyCreateSchema | 200 |
| `POST` | `/cpx/academy/upload` | 上传学习资源文件 | — | — | 200 |
| `PUT` | `/cpx/academy/update/{id}` | 修改学院内容 | id(path) | AcademyUpdateSchema | 200 |
| `PUT` | `/cpx/academy/publish/{id}` | 发布 / 下架切换 | id(path) | — | 200 |

## 公告管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/announcement/{id}` | 删除公告 | id(path) | — | 200 |
| `GET` | `/cpx/announcement/list` | 分页查询公告 | — | — | 200 |
| `GET` | `/cpx/announcement/detail/{id}` | 获取公告详情 | id(path) | — | 200 |
| `GET` | `/cpx/announcement/active` | App 端：当前生效公告列表 | — | — | 200 |
| `GET` | `/cpx/announcement/active/{id}` | App 端：公告详情 | id(path) | — | 200 |
| `POST` | `/cpx/announcement/create` | 新增公告 | — | AnnouncementCreateSchema | 200 |
| `PUT` | `/cpx/announcement/update/{id}` | 修改公告 | id(path) | AnnouncementUpdateSchema | 200 |
| `PUT` | `/cpx/announcement/publish/{id}` | 发布公告 | id(path) | — | 200 |
| `PUT` | `/cpx/announcement/offline/{id}` | 下线公告 | id(path) | — | 200 |

## 医院用户管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/user/doctors` | 分页查询医生 | — | — | 200 |
| `GET` | `/cpx/user/auditors` | 分页查询审核员 | — | — | 200 |
| `GET` | `/cpx/user/detail/{id}` | 获取用户详情 | id(path) | — | 200 |
| `PATCH` | `/cpx/user/status/batch` | 批量启用/禁用用户 | — | UserStatusSchema | 200 |
| `POST` | `/cpx/user/doctor` | 新增医生 | — | DoctorCreateSchema | 200 |
| `POST` | `/cpx/user/auditor` | 新增审核员 | — | AuditorCreateSchema | 200 |
| `PUT` | `/cpx/user/doctor/{id}` | 修改医生 | id(path) | DoctorUpdateSchema | 200 |
| `PUT` | `/cpx/user/auditor/{id}` | 修改审核员 | id(path) | AuditorUpdateSchema | 200 |
| `PUT` | `/cpx/user/password/{id}` | 重置密码 | id(path) | app__plugin__module_cpx__user__schema__ResetPasswordSchema | 200 |

## 示例管理（9 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/example/demo/delete` | 删除示例 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/example/demo/detail/{id}` | 获取示例详情 | id(path) | — | 200 ResponseSchema_DemoOutSchema_ |
| `GET` | `/example/demo/list` | 分页查询示例 | search(query) | — | 200 ResponseSchema_PageResultSchema_DemoOutSchema__ |
| `PATCH` | `/example/demo/status/batch` | 批量修改示例状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/example/demo/create` | 创建示例 | — | DemoCreateSchema | 201 ResponseSchema_DemoOutSchema_ |
| `POST` | `/example/demo/export` | 导出示例 | — | — | 200 |
| `POST` | `/example/demo/import` | 导入示例 | — | — | 200 ResponseSchema_str_ |
| `POST` | `/example/demo/download/template` | 获取示例导入模板 | — | — | 200 |
| `PUT` | `/example/demo/update/{id}` | 修改示例 | id(path) | DemoUpdateSchema | 200 ResponseSchema_DemoOutSchema_ |

## 岗位管理（8 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/position/delete` | 删除岗位 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/position/list` | 查询岗位 | search(query) | — | 200 ResponseSchema_PageResultSchema_PositionOutSchema__ |
| `GET` | `/system/position/detail/{id}` | 查询岗位详情 | id(path) | — | 200 ResponseSchema_PositionOutSchema_ |
| `GET` | `/system/position/options` | 获取岗位下拉选项 | — | — | 200 ResponseSchema_list_dict_str__Union_int__str____ |
| `PATCH` | `/system/position/status/batch` | 批量修改岗位状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/position/create` | 创建岗位 | — | PositionCreateSchema | 201 ResponseSchema_PositionOutSchema_ |
| `POST` | `/system/position/export` | 导出岗位 | — | PositionQueryParam | 200 |
| `PUT` | `/system/position/update/{id}` | 修改岗位 | id(path) | PositionUpdateSchema | 200 ResponseSchema_PositionOutSchema_ |

## 存储源管理（8 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/storage/source/delete` | 删除存储源 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/storage/source/page` | 分页查询存储源 | search(query) | — | 200 ResponseSchema_PageResultSchema_StorageSourceOutSchema__ |
| `GET` | `/storage/source/list` | 查询存储源列表 | — | — | 200 ResponseSchema_list_StorageSourceOutSchema__ |
| `GET` | `/storage/source/detail/{id}` | 查询存储源详情 | id(path) | — | 200 ResponseSchema_StorageSourceOutSchema_ |
| `POST` | `/storage/source/create` | 创建存储源 | — | StorageSourceCreateSchema | 201 ResponseSchema_StorageSourceOutSchema_ |
| `POST` | `/storage/source/test/{id}` | 测试存储源连接 | id(path) | — | 200 ResponseSchema_bool_ |
| `POST` | `/storage/source/test` | 测试存储源连接(配置) | — | StorageSourceTestSchema | 200 ResponseSchema_bool_ |
| `PUT` | `/storage/source/update/{id}` | 修改存储源 | id(path) | StorageSourceUpdateSchema | 200 ResponseSchema_StorageSourceOutSchema_ |

## 增值服务管理（8 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/cpx/value-added/{id}` | 删除增值服务 | id(path) | — | 200 |
| `GET` | `/cpx/value-added/list` | 分页查询增值服务 | — | — | 200 |
| `GET` | `/cpx/value-added/detail/{id}` | 获取增值服务详情 | id(path) | — | 200 |
| `GET` | `/cpx/value-added/active` | App 端：已上线增值服务列表 | — | — | 200 |
| `POST` | `/cpx/value-added/create` | 新增增值服务 | — | ValueAddedCreateSchema | 200 |
| `PUT` | `/cpx/value-added/update/{id}` | 修改增值服务 | id(path) | ValueAddedUpdateSchema | 200 |
| `PUT` | `/cpx/value-added/online/{id}` | 上线增值服务 | id(path) | — | 200 |
| `PUT` | `/cpx/value-added/offline/{id}` | 下线增值服务 | id(path) | — | 200 |

## 缓存监控（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/monitor/cache/delete/name/{cache_name}` | 清除指定缓存名称的所有缓存 | cache_name(path) | — | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/monitor/cache/delete/key/{cache_key}` | 清除指定缓存键 | cache_key(path) | — | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/monitor/cache/clear` | 清除所有缓存 | — | — | 200 ResponseSchema_NoneType_ |
| `GET` | `/monitor/cache/info` | 获取缓存监控信息 | — | — | 200 ResponseSchema_CacheMonitorSchema_ |
| `GET` | `/monitor/cache/get/names` | 获取缓存名称列表 | — | — | 200 ResponseSchema_list_CacheInfoSchema__ |
| `GET` | `/monitor/cache/get/keys/{cache_name}` | 获取缓存键名列表 | cache_name(path) | — | 200 ResponseSchema_list_CacheInfoSchema__ |
| `GET` | `/monitor/cache/get/value/{cache_name}/{cache_key}` | 获取缓存值 | cache_name(path)，cache_key(path) | — | 200 ResponseSchema_CacheInfoSchema_ |

## 日志管理（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/log/login/delete` | 删除登录日志 | — | (自由对象) | 200 ResponseSchema |
| `DELETE` | `/system/log/operation/delete` | 删除操作日志 | — | (自由对象) | 200 ResponseSchema |
| `GET` | `/system/log/login/detail/{id}` | 获取登录日志详情 | id(path) | — | 200 ResponseSchema_LoginLogDetailOutSchema_ |
| `GET` | `/system/log/login/list` | 查询登录日志列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_LoginLogOutSchema__ |
| `GET` | `/system/log/operation/detail/{id}` | 获取操作日志详情 | id(path) | — | 200 ResponseSchema_OperationLogDetailOutSchema_ |
| `GET` | `/system/log/operation/list` | 获取操作日志列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_OperationLogOutSchema__ |
| `POST` | `/system/log/operation/export` | 导出操作日志 | — | OperationLogQueryParam | 200 |

## 公告通知（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/notice/delete` | 删除公告 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/notice/detail/{id}` | 获取公告详情 | id(path) | — | 200 ResponseSchema_NoticeOutSchema_ |
| `GET` | `/system/notice/list` | 查询公告 | search(query) | — | 200 ResponseSchema_PageResultSchema_NoticeOutSchema__ |
| `GET` | `/system/notice/available` | 获取全局启用公告 | — | — | 200 ResponseSchema_list_NoticeOutSchema__ |
| `PATCH` | `/system/notice/status/batch` | 批量修改公告状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/notice/create` | 创建公告 | — | NoticeCreateSchema | 201 ResponseSchema_NoticeOutSchema_ |
| `PUT` | `/system/notice/update/{id}` | 修改公告 | id(path) | NoticeUpdateSchema | 200 ResponseSchema_NoticeOutSchema_ |

## 版本管理（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/versions/delete` | 删除版本 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/versions/list` | 分页查询版本 | search(query) | — | 200 ResponseSchema_PageResultSchema_VersionOutSchema__ |
| `GET` | `/system/versions/published` | 已发布版本列表 | — | — | 200 ResponseSchema_list_VersionOutSchema__ |
| `GET` | `/system/versions/detail/{id}` | 获取版本详情 | id(path) | — | 200 ResponseSchema_VersionOutSchema_ |
| `POST` | `/system/versions/create` | 创建版本 | — | VersionCreateSchema | 201 ResponseSchema_VersionOutSchema_ |
| `PUT` | `/system/versions/update/{id}` | 修改版本 | id(path) | VersionUpdateSchema | 200 ResponseSchema_VersionOutSchema_ |
| `PUT` | `/system/versions/{id}/status` | 变更版本状态 | id(path) | VersionStatusSchema | 200 ResponseSchema_VersionOutSchema_ |

## 流程编排（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/task/workflow/flow/delete` | 删除工作流 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/task/workflow/flow/detail/{id}` | 工作流详情 | id(path) | — | 200 ResponseSchema_WorkflowOutSchema_ |
| `GET` | `/task/workflow/flow/list` | 工作流列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_WorkflowOutSchema__ |
| `POST` | `/task/workflow/flow/create` | 创建工作流 | — | WorkflowCreateSchema | 201 ResponseSchema_WorkflowOutSchema_ |
| `POST` | `/task/workflow/flow/publish/{id}` | 发布工作流 | id(path) | — | 200 ResponseSchema_WorkflowOutSchema_ |
| `POST` | `/task/workflow/flow/execute` | 执行工作流 | — | WorkflowExecuteSchema | 200 ResponseSchema_WorkflowExecuteResultSchema_ |
| `PUT` | `/task/workflow/flow/update/{id}` | 更新工作流 | id(path) | WorkflowUpdateSchema | 200 ResponseSchema_WorkflowOutSchema_ |

## 工作流节点（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/task/workflow/nodes/delete` | 删除节点 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/task/workflow/nodes/options` | 节点选项 | — | — | 200 ResponseSchema_list_dict__ |
| `GET` | `/task/workflow/nodes/detail/{id}` | 节点详情 | id(path) | — | 200 ResponseSchema_WorkflowNodeTypeOutSchema_ |
| `GET` | `/task/workflow/nodes/list` | 节点列表 | search(query) | — | 200 ResponseSchema_PageResultSchema_WorkflowNodeTypeOutSchema__ |
| `GET` | `/task/workflow/nodes/select` | 节点选择列表 | — | — | 200 ResponseSchema_list_dict__ |
| `POST` | `/task/workflow/nodes/create` | 创建节点 | — | WorkflowNodeTypeCreateSchema | 201 ResponseSchema_WorkflowNodeTypeOutSchema_ |
| `PUT` | `/task/workflow/nodes/update/{id}` | 更新节点 | id(path) | WorkflowNodeTypeUpdateSchema | 200 ResponseSchema_WorkflowNodeTypeOutSchema_ |

## 病例审核（7 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/audit/workbench` | 审核工作台统计 | — | — | 200 |
| `GET` | `/cpx/audit/pending` | 待审核病例列表 | — | — | 200 |
| `GET` | `/cpx/audit/detail/{case_id}` | 病例审核详情（含校验提示） | case_id(path) | — | 200 |
| `GET` | `/cpx/audit/history` | 审核记录 | — | — | 200 |
| `POST` | `/cpx/audit/approve` | 审核通过 | — | AuditApproveSchema | 200 |
| `POST` | `/cpx/audit/reject` | 审核驳回 | — | AuditRejectSchema | 200 |
| `PUT` | `/cpx/audit/record/{record_id}` | 修改审核记录 | record_id(path) | AuditRecordUpdateSchema | 200 |

## 部门管理（6 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/dept/delete` | 删除部门 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/dept/tree` | 查询部门树 | — | — | 200 ResponseSchema_list_DeptOutSchema__ |
| `GET` | `/system/dept/detail/{id}` | 查询部门详情 | id(path) | — | 200 ResponseSchema_DeptOutSchema_ |
| `PATCH` | `/system/dept/status/batch` | 批量修改部门状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/dept/create` | 创建部门 | — | DeptCreateSchema | 201 ResponseSchema_DeptOutSchema_ |
| `PUT` | `/system/dept/update/{id}` | 修改部门 | id(path) | DeptUpdateSchema | 200 ResponseSchema_DeptOutSchema_ |

## 菜单管理（6 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/system/menu/delete` | 删除菜单 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/system/menu/tree` | 查询菜单树 | — | — | 200 ResponseSchema_list_MenuOutSchema__ |
| `GET` | `/system/menu/detail/{id}` | 查询菜单详情 | id(path) | — | 200 ResponseSchema_MenuOutSchema_ |
| `PATCH` | `/system/menu/status/batch` | 批量修改菜单状态 | — | BatchSetAvailable | 200 ResponseSchema_NoneType_ |
| `POST` | `/system/menu/create` | 创建菜单 | — | MenuCreateSchema | 201 ResponseSchema_MenuOutSchema_ |
| `PUT` | `/system/menu/update/{id}` | 修改菜单 | id(path) | MenuUpdateSchema | 200 ResponseSchema_MenuOutSchema_ |

## 存储文件（6 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/storage/file/delete` | 删除存储源文件 | — | Body_delete_storage_file_controller_storage_file_delete_delete | 200 ResponseSchema_NoneType_ |
| `GET` | `/storage/file/list` | 查询存储源文件列表 | — | — | 200 ResponseSchema_list_StorageObject__ |
| `GET` | `/storage/file/url` | 获取文件访问URL | remote_path(query) | — | 200 ResponseSchema_Union_str__NoneType__ |
| `POST` | `/storage/file/upload` | 上传文件到存储源 | — | — | 200 ResponseSchema_dict_ |
| `POST` | `/storage/file/download` | 下载存储源文件 | — | Body_download_storage_file_controller_storage_file_download_post | 200 |
| `POST` | `/storage/file/copy` | 复制/移动文件 | — | Body_copy_or_move_storage_file_controller_storage_file_copy_post | 200 ResponseSchema_dict_ |

## 文件传输（6 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/storage/transfer/task` | 删除传输任务 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `GET` | `/storage/transfer/task/page` | 分页查询传输任务 | search(query) | — | 200 ResponseSchema_PageResultSchema_TransferTaskOutSchema__ |
| `GET` | `/storage/transfer/task/{id}` | 查询传输任务详情 | id(path) | — | 200 ResponseSchema_TransferTaskOutSchema_ |
| `POST` | `/storage/transfer/task` | 创建传输任务(远端源) | — | TransferTaskCreateSchema | 200 ResponseSchema_dict_ |
| `POST` | `/storage/transfer/task/upload` | 创建传输任务(本地上传源) | — | — | 200 ResponseSchema_dict_ |
| `POST` | `/storage/transfer/task/{id}/cancel` | 取消传输任务 | id(path) | — | 200 ResponseSchema_NoneType_ |

## 医院管理（6 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/hospital/list` | 分页查询医院 | — | — | 200 |
| `GET` | `/cpx/hospital/all` | 全部启用医院（下拉选项） | — | — | 200 |
| `GET` | `/cpx/hospital/detail/{id}` | 获取医院详情 | id(path) | — | 200 |
| `PATCH` | `/cpx/hospital/status/batch` | 批量启用/禁用医院 | — | HospitalStatusSchema | 200 |
| `POST` | `/cpx/hospital/create` | 新增医院 | — | HospitalCreateSchema | 200 |
| `PUT` | `/cpx/hospital/update/{id}` | 修改医院 | id(path) | HospitalUpdateSchema | 200 |

## 在线用户（5 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `DELETE` | `/monitor/online/delete` | 强制下线 | — | (自由对象) | 200 ResponseSchema_NoneType_ |
| `DELETE` | `/monitor/online/clear` | 清除所有在线用户 | — | — | 200 ResponseSchema_NoneType_ |
| `GET` | `/monitor/online/list` | 获取在线用户列表 | search(query) | — | 200 ResponseSchema_list_OnlineOutSchema__ |
| `GET` | `/monitor/online/current` | 获取当前用户的在线会话 | — | — | 200 ResponseSchema_list_OnlineOutSchema__ |
| `GET` | `/monitor/online/stats` | 获取仪表盘统计数据 | — | — | 200 ResponseSchema_DashboardStatsSchema_ |

## 健康检查（4 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/common/health/check` | 健康检查 | — | — | 200 ResponseSchema_HealthOut_ |
| `GET` | `/common/health/live` | 存活探针 | — | — | 200 ResponseSchema_HealthOut_ |
| `GET` | `/common/health/ready` | 就绪探针 | — | — | 200 ResponseSchema_ReadinessOut_ |
| `GET` | `/common/health/stream` | 健康状态实时推送 | — | — | — |

## 业务登录认证（3 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/auth/userinfo` | 当前用户信息 | — | — | 200 |
| `POST` | `/cpx/auth/login` | 业务登录 | — | LoginSchema | 200 |
| `POST` | `/cpx/auth/logout` | 业务登出 | — | — | 200 |

## 文件管理（2 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `POST` | `/common/file/upload` | 上传文件 | — | — | 200 ResponseSchema_UploadResponseSchema_ |
| `POST` | `/common/file/download` | 下载文件 | — | Body_download_controller_common_file_download_post | 200 |

## 参数管理（2 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/system/param/info` | 获取初始化缓存参数 | — | — | 200 ResponseSchema_list_ParamsOutSchema__ |
| `PUT` | `/system/param/update/{id}` | 修改参数 | id(path) | ParamsUpdateSchema | 200 ResponseSchema_ParamsOutSchema_ |

## AI知识库（2 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/ai/kb/status` | 知识库状态（已导入文件与分片数） | — | — | 200 ResponseSchema_dict_str__Any__ |
| `POST` | `/ai/kb/ask` | 知识库问答（基于胸痛中心认证标准 PDF） | — | (自由对象) | 200 ResponseSchema_dict_str__Any__ |

## 系统日志（2 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/log/roles` | 用户角色选项（日志筛选） | — | — | 200 |
| `GET` | `/cpx/log/list` | 分页查询系统日志 | — | — | 200 |

## 数据统计（2 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/cpx/stats/dashboard` | 数据驾驶舱统计 | — | — | 200 |
| `GET` | `/cpx/stats/analysis` | 统计分析 | — | — | 200 |

## 服务器监控（1 个接口）

| 方法 | 路径 | 接口说明 | 必填参数 | 请求体 | 主要响应 |
|---|---|---|---|---|---|
| `GET` | `/monitor/server/info` | 查询服务器监控信息 | — | — | 200 ResponseSchema_ServerMonitorSchema_ |
