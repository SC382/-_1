# -*- coding: utf-8 -*-
"""医生端路由 /cpx/doctor/*（仅医生角色，操作自动写入系统日志）"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import httpx, json

from app.common.response import SuccessResponse
from app.core.exceptions import CustomException
from app.config.setting import settings
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_DOCTOR, BizAuth, BusinessRole
from app.plugin.module_cpx.doctor.schema import (
    CaseCreateSchema,
    CaseUpdateSchema,
    FollowUpSubmitSchema,
    FormSaveSchema,
    PasswordChangeSchema,
)
from app.plugin.module_cpx.doctor.service import DoctorService
from app.plugin.module_cpx.log.service import LogService, get_client_ip
from app.plugin.module_cpx.fields import FIELDS as _CPX_FIELDS

# ── 标准字段字典（供 AI 识别提示，与 fields.py 的 FIELDS 同步）──────────
_TAB_NAMES = {"basic": "基本信息", "prehospital": "院前急救", "triage": "急诊分诊",
              "exam": "检验检查", "treatment": "院内诊疗", "pci": "介入手术", "outcome": "患者转归"}
def _build_field_dict_text() -> str:
    if not _CPX_FIELDS:
        return ""
    by_tab: dict = {}
    for f in _CPX_FIELDS:
        by_tab.setdefault(f.get("tab", "other"), []).append(f)
    lines = []
    for tab, fs in by_tab.items():
        lines.append(f"【{_TAB_NAMES.get(tab, tab)}】")
        for f in fs:
            opt = ""
            if f.get("options"):
                opt = "（可选值：" + "/".join(o["value"] for o in f["options"]) + "）"
            lines.append(f"  - {f['code']} {f['name']}{opt}")
    return "\n".join(lines)
_FIELD_DICT_TEXT = _build_field_dict_text()


def _resolve_image_data_uri(image_url: str) -> str:
    """把图片 URL 转成 base64 data URI（DeepSeek/千问服务器拉不到本地图片，必须内联）。

    - data: 开头 → 原样
    - 本机地址（127.0.0.1/localhost/局域网 IP）或 /static 相对路径 → 读磁盘文件转 base64
    - 公网 http(s) → 原样透传（模型服务自行下载）
    """
    import base64 as _b64
    import mimetypes
    from pathlib import Path as _Path
    from urllib.parse import urlparse

    from app.config.path_conf import STATIC_DIR

    if image_url.startswith("data:"):
        return image_url
    path = image_url
    if "://" in path:
        parsed = urlparse(path)
        host = (parsed.hostname or "").lower()
        if host in ("127.0.0.1", "localhost", "0.0.0.0", "::1") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
            path = parsed.path
        else:
            return image_url
    # 去掉 /api/v1/static/ 或 /static/ 前缀，映射到磁盘 STATIC_DIR
    if "/api/v1/static/" in path:
        path = path.split("/api/v1/static/", 1)[1]
    elif "/static/" in path:
        path = path.split("/static/", 1)[1]
    else:
        return image_url
    f = STATIC_DIR / path
    if f.exists() and f.is_file():
        mime = mimetypes.guess_type(str(f))[0] or "image/png"
        return f"data:{mime};base64,{_b64.b64encode(f.read_bytes()).decode()}"
    return image_url
from app.api.v1.module_ai.kb.service import KbService

DoctorRouter = APIRouter(prefix="/doctor", tags=["医生端"])


def _to_abs_url(request: Request, path: str | None) -> str | None:
    """把后端返回的相对路径（如 /api/v1/static/...）补全为绝对 URL。

    app 端（H5/App）接口直连后端 8002、且本地没有 vite 代理，
    相对路径会被 <image> 解析到 app 自己的端口（5190）→ 404。
    按请求 host 拼绝对地址，图片即可直接访问。
    """
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    # 注意不能用 request.base_url（FastAPI 下它带 /api/v1 前缀），用 scheme://netloc
    host = f"{request.url.scheme}://{request.url.netloc}"
    return host + "/" + path.lstrip("/")


@DoctorRouter.get("/stats", summary="医生工作台统计")
async def get_stats_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).stats()
    return SuccessResponse(data=result, msg="查询工作台统计成功")


@DoctorRouter.get("/me", summary="当前医生基本信息")
async def get_me_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).me()
    return SuccessResponse(data=result, msg="查询成功")


@DoctorRouter.get("/templates", summary="已发布模板列表（含字段）")
async def get_templates_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).templates()
    return SuccessResponse(data=result, msg="查询模板成功")


@DoctorRouter.post("/case/create", summary="患者快速建档（生成病例编号）")
async def create_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    data: Annotated[CaseCreateSchema, Body(description="建档参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.create(data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="新建病例",
        description=f"医生 {auth.user.real_name} 创建病例 {result['case_no']}（患者 {data.patient_name}）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="建档成功")


@DoctorRouter.put("/case/{id}", summary="更新患者基础信息")
async def update_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    data: Annotated[CaseUpdateSchema, Body(description="更新参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="修改病例",
        description=f"医生 {auth.user.real_name} 修改病例 {result['case_no']} 基础信息",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="更新成功")


@DoctorRouter.post("/case/{id}/save", summary="保存病例表单（草稿）")
async def save_form_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    data: Annotated[FormSaveSchema, Body(description="表单数据")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.save_form(id=id, template_id=data.template_id, form_data=data.form_data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="保存草稿",
        description=f"医生 {auth.user.real_name} 保存病例 {result['case_no']} 表单草稿",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="草稿已保存")


@DoctorRouter.post("/case/{id}/submit", summary="提交病例审核")
async def submit_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.submit(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="提交审核",
        description=f"医生 {auth.user.real_name} 提交病例 {result['case_no']} 进入审核",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="提交成功，已进入审核")


@DoctorRouter.get("/case/list", summary="我的病例列表")
async def list_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    status: str | None = Query(default=None, description="状态 draft/submitted/approved/rejected"),
    keyword: str | None = Query(default=None, description="患者姓名/病例编号"),
    start_time: str | None = Query(default=None, description="开始时间 yyyy-MM-dd"),
    end_time: str | None = Query(default=None, description="结束时间 yyyy-MM-dd"),
    diagnose_type: str | None = Query(default=None, description="诊断类型"),
    come_type: str | None = Query(default=None, description="来院方式"),
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.my_list(
        page_no=page_no,
        page_size=page_size,
        status=status,
        keyword=keyword,
        start_time=start_time,
        end_time=end_time,
        diagnose_type=diagnose_type,
        come_type=come_type,
    )
    return SuccessResponse(data=result, msg="查询我的病例成功")


@DoctorRouter.get("/field-dict", summary="胸痛标准字段字典")
async def field_dict_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).field_dict()
    return SuccessResponse(data=result, msg="查询字段字典成功")


@DoctorRouter.get("/case/{id}/timeline", summary="救治时间轴（含关键指标）")
async def timeline_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).timeline(id=id)
    return SuccessResponse(data=result, msg="查询时间轴成功")


@DoctorRouter.get("/case/{id}/analysis", summary="单病例质控分析")
async def analysis_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).analysis(id=id)
    return SuccessResponse(data=result, msg="查询病例分析成功")


@DoctorRouter.get("/case/{id}", summary="病例详情（含审核反馈）")
async def detail_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="查询病例详情成功")


@DoctorRouter.delete("/case/{id}", summary="删除我的病例（仅本人，级联删除关联数据）")
async def delete_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).delete_case(id=id)
    return SuccessResponse(data=result, msg="病例已删除")


@DoctorRouter.post("/password", summary="修改登录密码")
async def change_password_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    data: Annotated[PasswordChangeSchema, Body(description="密码参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    await service.change_password(old_password=data.old_password, new_password=data.new_password)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="用户管理",
        operation="修改密码",
        description=f"医生 {auth.user.real_name} 修改了登录密码",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="密码修改成功")


@DoctorRouter.post("/followup/generate", summary="为已通过病例生成随访计划")
async def followup_generate_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.followup_generate()
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="随访管理",
        operation="生成随访计划",
        description=f"医生 {auth.user.real_name} 生成随访计划 {result['generated']} 条",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="随访计划已生成")


@DoctorRouter.get("/followup/list", summary="我的随访列表")
async def followup_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    status: str | None = Query(default=None, description="状态 pending/submitted/overdue"),
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.followup_list(page_no=page_no, page_size=page_size, status=status)
    return SuccessResponse(data=result, msg="查询随访列表成功")


@DoctorRouter.get("/followup/groups", summary="随访按患者聚合列表")
async def followup_groups_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    status: str | None = Query(default=None, description="状态 pending/submitted/overdue（按组筛选）"),
) -> JSONResponse:
    result = await DoctorService(auth, db).followup_groups(status=status)
    return SuccessResponse(data=result, msg="查询随访分组成功")


@DoctorRouter.get("/followup/{id}", summary="随访单条详情（含患者上下文）")
async def followup_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="随访ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).followup_detail(id=id)
    return SuccessResponse(data=result, msg="查询随访详情成功")


@DoctorRouter.post("/followup/{id}/submit", summary="提交随访表单")
async def followup_submit_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="随访ID")],
    data: Annotated[FollowUpSubmitSchema, Body(description="随访参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    result = await service.followup_submit(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="随访管理",
        operation="提交随访",
        description=f"医生 {auth.user.real_name} 提交随访记录 #{id}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="随访已提交")


@DoctorRouter.get("/stats/overview", summary="数据概览（累计/诊断分布/趋势）")
async def stats_overview_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    months: int = Query(default=6, ge=1, le=12, description="统计月份数（月度指标用）"),
) -> JSONResponse:
    result = await DoctorService(auth, db).stats_overview(months=months)
    return SuccessResponse(data=result, msg="查询数据概览成功")


@DoctorRouter.get("/units", summary="救治医院列表")
async def units_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).units()
    return SuccessResponse(data=result, msg="查询救治医院成功")


@DoctorRouter.post("/ecg/upload", summary="远程心电上传（AI 诊断 + 病例快照）")
async def ecg_upload_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    case_id: int | None = Query(default=None, description="关联病例ID（可选）"),
    image_path: str | None = Query(default=None, description="心电图图片路径（可选）"),
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_upload(case_id=case_id, image_path=image_path)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="远程心电",
        operation="心电诊断",
        description=f"医生 {auth.user.real_name} 提交远程心电诊断（关联病例 {case_id or '-'}）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="心电AI诊断完成")


@DoctorRouter.get("/ecg/list", summary="远程心电记录列表（发起+接收合并）")
async def ecg_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_list()
    for it in (result.get("items") or []):
        it["image_path"] = _to_abs_url(request, it.get("image_path"))
    return SuccessResponse(data=result, msg="查询心电记录成功")


@DoctorRouter.get("/ecg/list-by-case/{case_id}", summary="某病例心电记录列表（供随访心电图联动）")
async def ecg_list_by_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    case_id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_list_by_case(case_id=case_id)
    for it in (result.get("items") or []):
        it["image_path"] = _to_abs_url(request, it.get("image_path"))
    return SuccessResponse(data=result, msg="查询心电记录成功")


@DoctorRouter.get("/ecg/detail/{id}", summary="远程心电详情")
async def ecg_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="记录ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_detail(id=id)
    result["image_path"] = _to_abs_url(request, result.get("image_path"))
    return SuccessResponse(data=result, msg="查询成功")


@DoctorRouter.post("/ecg/send-consult/{id}", summary="申请协同会诊（选接收医院）")
async def ecg_send_consult_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="记录ID")],
    body: Annotated[dict, Body(description="target_hospital_id")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_send_consult(
        id=id, target_hospital_id=int(body["target_hospital_id"]),
    )
    await LogService.create(
        db, user_id=auth.user.id, module="远程心电", operation="申请协同",
        description=f"医生 {auth.user.real_name} 申请协同会诊：记录 {id} → 医院 {body['target_hospital_id']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="协同申请已发送")


@DoctorRouter.post("/ecg/feedback/{id}", summary="接收方医生写反馈（结束会诊）")
async def ecg_feedback_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="记录ID")],
    body: Annotated[dict, Body(description="feedback")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    result = await DoctorService(auth, db).ecg_feedback(id=id, feedback=str(body["feedback"]))
    await LogService.create(
        db, user_id=auth.user.id, module="远程心电", operation="会诊反馈",
        description=f"医生 {auth.user.real_name} 反馈心电会诊：记录 {id}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="反馈已提交")


@DoctorRouter.get("/selfcheck", summary="AI 模拟再认证自评")
async def selfcheck_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    start: str | None = Query(default=None, description="开始时间 yyyy-MM-dd"),
    end: str | None = Query(default=None, description="结束时间 yyyy-MM-dd"),
) -> JSONResponse:
    result = await DoctorService(auth, db).selfcheck(start=start, end=end)
    return SuccessResponse(data=result, msg="自评完成")


@DoctorRouter.post("/kb/ask", summary="认证知识库 AI 问答（医生端，回答标注来源文件与页码）")
async def doctor_kb_ask_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    body: Annotated[dict, Body(description='{"question": "问题"}')],
) -> JSONResponse:
    question = str(body.get("question", "")).strip()
    if not question:
        raise CustomException(msg="问题不能为空")
    result = await KbService(None).ask(question)
    return SuccessResponse(data=result, msg="知识库回答生成成功")


@DoctorRouter.post("/ai/recognize", summary="AI 图片/文字识别：通义千问 Vision / 文字解析提取患者信息")
async def ai_recognize_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    body: Annotated[dict, Body(description='{"image_url": "图片URL"} 或 {"text": "文字内容"}')],
) -> JSONResponse:
    image_url = (body.get("image_url") or "").strip()
    text = (body.get("text") or "").strip()
    if not image_url and not text:
        raise CustomException(msg="请提供 image_url 或 text 参数")

    if image_url:
        # 图片识别：AI 自主判断图片中的字段并提取
        prompt = (
            "你是胸痛中心医疗信息提取助手。请仔细识别这张图片中的全部文字（包括表头、每一栏标签及其对应数值、"
            "所有时间节点、生命体征、诊断、用药等），提取与患者相关的信息。\n\n"
            "标准字段编码字典（图片中出现的字段，务必用这里的 key 输出）：\n"
            f"{_FIELD_DICT_TEXT}\n\n"
            "规则（必须严格遵守）：\n"
            "1. 只提取图片中清晰可读的信息，绝不编造或推测图片里没有的内容\n"
            "2. **全量提取**：图片中只要出现了字典里的任何字段，就提取其对应值；可跨多个区块/表格提取\n"
            "3. **key 必须用上面的标准编码**（如 fmc_time、onset_time、balloon_time、troponin_time 等时间节点也要识别）\n"
            "4. 图片中出现但不在字典里的字段，也请用语义化英文 key 输出，不要丢弃\n"
            "5. 提取内容须与图片文字一致，不润色、不重组\n"
            "6. 若字段标注了【可选值】，请把识别/判断结果**归一化到其中一个可选值**；"
            "例如 card_type 证件类型，请依据证件上的标题文字与卡片样式判断属于 身份证 / 医保卡 / 其他\n"
            "7. **日期格式必须统一**：日期型字段一律输出 YYYY-MM-DD（如 1968-03-12，不要写 1968年3月12日）；"
            "日期时间型字段一律输出 YYYY-MM-DD HH:MM（如 2026-08-28 14:30）\n\n"
            "只返回纯JSON对象，不要任何解释或markdown格式。"
        )
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": _resolve_image_data_uri(image_url), "detail": "high"}},
            {"type": "text", "text": prompt},
        ]}]
        model = settings.ZHIPU_VISION_MODEL or "glm-4v-flash"
        base_url = settings.ZHIPU_BASE_URL
        api_key = settings.ZHIPU_API_KEY
    else:
        # 文字解析：AI 自主判断文本中的字段并提取
        prompt = (
            "你是胸痛中心医疗信息提取助手。从以下文字中提取患者相关信息。\n\n"
            "标准字段编码字典（文字中出现的字段，请用这里的 key 输出）：\n"
            f"{_FIELD_DICT_TEXT}\n\n"
            "规则：\n"
            "1. 只提取文字中明确出现的信息，绝不编造；没有出现的信息不要输出\n"
            "2. **全量提取**：只要文字里出现了字典中的任何字段，就提取其值\n"
            "3. **key 必须用上面的标准编码**（含 fmc_time、onset_time、balloon_time、troponin_time 等时间节点）\n"
            "4. 文字中出现但不在字典里的字段，也用语义化英文 key 输出，不要丢弃\n"
            "5. 若字段标注了【可选值】，请把识别/判断结果归一化到其中一个可选值（如 card_type→身份证/医保卡/其他）\n"
            "6. **日期格式必须统一**：日期型一律 YYYY-MM-DD（如 1968-03-12）；日期时间型一律 YYYY-MM-DD HH:MM\n"
            "7. 只返回纯JSON，无解释无markdown\n\n"
            f"文字内容：{text}"
        )
        messages = [{"role": "user", "content": prompt}]
        model = settings.OPENAI_TEXT_MODEL or settings.DEEPSEEK_MODEL or "deepseek-chat"
        base_url = settings.DEEPSEEK_BASE_URL
        api_key = settings.DEEPSEEK_API_KEY

    if not api_key or api_key.startswith("sk-placeholder"):
        raise CustomException(msg="未配置 AI API Key：图片识别需 ZHIPU_API_KEY，文字解析需 DEEPSEEK_API_KEY")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 1024, "temperature": 0.1},
            )
            resp.raise_for_status()
            data = resp.json()
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
    except Exception as e:
        raise CustomException(msg=f"AI 服务调用失败：{e}") from e

    if not content:
        raise CustomException(msg="AI 未返回有效内容")
    # 提取 JSON（兼容 ```json 包裹）
    raw = content
    if "```" in content:
        parts = content.split("```")
        raw = parts[1].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise json.JSONDecodeError("not dict", raw, 0)
        return SuccessResponse(data=result, msg="AI 识别成功")
    except json.JSONDecodeError:
        return SuccessResponse(data={"raw_text": content}, msg="AI 返回文本（请核对）")


@DoctorRouter.post("/ai/asr", summary="AI 语音识别（智谱 GLM-ASR-2512 音频转写）")
async def ai_asr_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    body: Annotated[dict, Body(description='{"audio_base64": "音频 base64 编码", "format": "wav|mp3"}')],
) -> JSONResponse:
    audio = (body.get("audio_base64") or "").strip()
    if not audio:
        raise CustomException(msg="请提供 audio_base64（音频 base64 编码）")
    if not settings.ZHIPU_API_KEY or settings.ZHIPU_API_KEY.startswith("sk-placeholder"):
        raise CustomException(msg="未配置智谱 API Key（请在 env/.env.dev 配置 ZHIPU_API_KEY）")
    model = settings.ZHIPU_ASR_MODEL or "glm-asr-2512"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                settings.ZHIPU_BASE_URL.rstrip("/") + "/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.ZHIPU_API_KEY}"},
                files={
                    "model": (None, model),
                    "stream": (None, "false"),
                    "file_base64": (None, audio),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        text = (data.get("text") or "").strip()
    except Exception as e:
        raise CustomException(msg=f"语音识别失败：{e}") from e
    if not text:
        raise CustomException(msg="语音识别未返回文本")
    return SuccessResponse(data={"text": text}, msg="语音识别成功")


@DoctorRouter.get("/meeting/templates", summary="三会模板列表")
async def meeting_templates_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    return SuccessResponse(
        data=[{"type": k, "name": v["name"], "desc": v["desc"]} for k, v in DoctorService.MEETING_TYPES.items()],
        msg="查询模板成功",
    )


@DoctorRouter.post("/meeting/generate", summary="生成三会 PPT")
async def meeting_generate_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    meeting_type: str = Query(default="quality", description="quality/joint/case"),
    start: str | None = Query(default=None, description="开始时间 yyyy-MM-dd"),
    end: str | None = Query(default=None, description="结束时间 yyyy-MM-dd"),
    case_id: int | None = Query(default=None, description="典型病例讨论会：指定病例ID"),
) -> JSONResponse:
    result = await DoctorService(auth, db).meeting_generate(meeting_type=meeting_type, start=start, end=end, case_id=case_id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="三会模板",
        operation="生成PPT",
        description=f"医生 {auth.user.real_name} 生成三会 PPT《{result['title']}》",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="PPT 生成成功")


@DoctorRouter.get("/meeting/list", summary="三会 PPT 生成记录")
async def meeting_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).meeting_list()
    return SuccessResponse(data=result, msg="查询记录成功")


@DoctorRouter.get("/meeting/{id}", summary="会议内容预览")
async def meeting_preview_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="记录ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await DoctorService(auth, db).meeting_preview(id=id)
    return SuccessResponse(data=result, msg="查询预览成功")


@DoctorRouter.delete("/meeting/{id}", summary="删除生成记录")
async def meeting_delete_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="记录ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = DoctorService(auth, db)
    await service.meeting_delete(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="三会模板",
        operation="删除PPT",
        description=f"医生 {auth.user.real_name} 删除三会 PPT 记录 #{id}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="删除成功")


@DoctorRouter.post("/upload/image", summary="上传图片（病历/心电图等）")
async def upload_image_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    file: UploadFile = File(..., description="图片文件"),
) -> JSONResponse:
    url = await DoctorService(auth, db).upload_image(file)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="上传图片",
        description=f"医生 {auth.user.real_name} 上传图片",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data={"url": url}, msg="上传成功")
