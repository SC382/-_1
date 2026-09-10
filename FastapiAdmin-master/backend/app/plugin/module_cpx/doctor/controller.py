# -*- coding: utf-8 -*-
"""医生端路由 /cpx/doctor/*（仅医生角色，操作自动写入系统日志）"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import base64, httpx, json

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
from app.plugin.module_cpx.doctor.tencent_ocr import idcard_ocr as _tencent_idcard_ocr
from app.plugin.module_cpx.doctor.tencent_ocr import general_ocr as _tencent_general_ocr
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

    注意：站内相对路径可能带静态文件签名参数（?exp=&sign=，见 core/signed_url.py），
    解析磁盘文件前必须先剥离查询串，否则会拼出带 ? 的文件名导致找不到文件，
    进而把无法访问的相对 URL 直接传给模型服务造成 400。
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
    # 剥离静态文件签名等查询串（?exp=&sign=）与锚点，仅保留真实路径部分
    path = path.split("?", 1)[0].split("#", 1)[0]
    # 去掉 /api/v1/static/ 或 /static/ 前缀，映射到磁盘 STATIC_DIR
    if "/api/v1/static/" in path:
        path = path.split("/api/v1/static/", 1)[1]
    elif "/static/" in path:
        path = path.split("/static/", 1)[1]
    else:
        return image_url
    f = STATIC_DIR / path
    # 安全：规范化后必须仍在 STATIC_DIR 内，防止 ../../ 路径穿越读取任意文件
    try:
        if not f.resolve().is_relative_to(_Path(STATIC_DIR).resolve()):
            return image_url
    except (OSError, ValueError):
        return image_url
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
            "例如 card_type 证件类型，请依据证件上的标题文字与卡片样式判断属于 身份证 / 医保卡 / 其他。"
            "**特别注意**：身份证卡面上的『公民身份号码』『证件号码』『号码』等字样是身份证号一栏的标题文字，不是证件类型，"
            "严禁把 card_type 识别成『公民身份号码』；只要卡片样式或标题表明是身份证，card_type 一律输出 身份证\n"
            "7. **日期格式必须统一**：日期型字段一律输出 YYYY-MM-DD（如 1968-03-12，不要写 1968年3月12日）；"
            "日期时间型字段一律输出 YYYY-MM-DD HH:MM（如 2026-08-28 14:30）\n"
            "8. **只输出字段值本身**，不要带字段名/标签/冒号前缀"
            "（如 insurance_no 输出 YB20260828001，而不是「医保卡号：YB20260828001」）\n\n"
            "只返回纯JSON对象，不要任何解释或markdown格式。"
        )
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": _resolve_image_data_uri(image_url), "detail": "high"}},
            {"type": "text", "text": prompt},
        ]}]
        model = settings.ZHIPU_VISION_MODEL or "glm-4v-flash"
        base_url = settings.ZHIPU_BASE_URL
        api_key = settings.ZHIPU_API_KEY
        # 智谱视觉模型 max_tokens 硬上限 1024（超出报 1210），不可上调
        max_tokens = 1024
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
            "7. **只输出字段值本身**，不要带字段名/标签/冒号前缀"
            "（如 insurance_no 输出 YB20260828001，而不是「医保卡号：YB20260828001」）\n"
            "8. 只返回纯JSON，无解释无markdown\n\n"
            f"文字内容：{text}"
        )
        messages = [{"role": "user", "content": prompt}]
        model = settings.OPENAI_TEXT_MODEL or settings.DEEPSEEK_MODEL or "deepseek-chat"
        base_url = settings.DEEPSEEK_BASE_URL
        api_key = settings.DEEPSEEK_API_KEY
        # 文字解析走 DeepSeek：下方请求体已关闭思考（thinking.disabled），输出预算基本全部
        # 留给 JSON 正文，4096 足够；若网关不支持该参数，仍有 reasoning_content 兜底 + 截断检测，
        # 不会静默返回半截数据
        max_tokens = 4096

    if not api_key or api_key.startswith("sk-placeholder"):
        raise CustomException(msg="未配置 AI API Key：图片识别需 ZHIPU_API_KEY，文字解析需 DEEPSEEK_API_KEY")
    req_body: dict = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1}
    if not image_url:
        # 结构化抽取无需长链思考：deepseek-v4-flash 默认产出大量 reasoning，
        # 实测同一段文字思考独占 4096~8000 tokens、耗时 18s，把输出预算挤满导致 JSON 正文被截断；
        # 关闭思考后约 1.5s / 400 tokens 即返回完整 JSON，字段覆盖相当。
        req_body["thinking"] = {"type": "disabled"}
    # 兼容个别网关不认 thinking 参数：返回 400 时去掉该参数重试一次
    payloads = (
        [req_body, {k: v for k, v in req_body.items() if k != "thinking"}]
        if "thinking" in req_body
        else [req_body]
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            for idx, payload in enumerate(payloads):
                resp = await client.post(
                    base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 400 and idx < len(payloads) - 1:
                    continue
                resp.raise_for_status()
                break
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            # 推理型模型（deepseek-v4-flash）思考草稿在 reasoning_content、正文在 content；
            # content 被挤空时兜底取 reasoning_content，避免整次识别直接失败
            content = (message.get("reasoning_content") or "").strip()
        # finish_reason=length 表示输出被 max_tokens 截断，此时 JSON 必然不完整
        truncated = choice.get("finish_reason") == "length"
    except Exception as e:
        raise CustomException(msg=f"AI 服务调用失败：{e}") from e

    if not content:
        raise CustomException(msg="AI 未返回有效内容，请重试")
    # 提取 JSON（兼容 ```json 包裹）
    raw = content
    if "```" in content:
        parts = content.split("```")
        raw = parts[1].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    # 依次尝试：整段解析 → 截取首个 { 到末个 } 再解析（容忍前后夹带的说明性文字）
    candidates = [raw]
    _start, _end = raw.find("{"), raw.rfind("}")
    if _start >= 0 and _end > _start:
        candidates.append(raw[_start : _end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return SuccessResponse(data=obj, msg="AI 识别成功")
    if truncated:
        raise CustomException(msg="AI 输出被截断（录入内容过长），请精简后重试或分次录入")
    return SuccessResponse(data={"raw_text": content}, msg="AI 返回文本（请核对）")


@DoctorRouter.post("/ai/ocr", summary="证件 OCR 识别（腾讯云：身份证 IDCardOCR / 医保卡通用印刷体）")
async def ai_ocr_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    body: Annotated[dict, Body(description='{"image_url": "图片URL", "card_type": "身份证|医保卡"}')],
) -> JSONResponse:
    image_url = (body.get("image_url") or "").strip()
    card_type = (body.get("card_type") or "身份证").strip()
    if not image_url:
        raise CustomException(msg="请提供 image_url 参数")
    if card_type not in ("身份证", "医保卡"):
        raise CustomException(msg=f"暂不支持识别证件类型：{card_type}")
    secret_id = settings.TENCENT_OCR_SECRET_ID
    secret_key = settings.TENCENT_OCR_SECRET_KEY
    if not secret_id or not secret_key or secret_id.startswith("<请填写"):
        raise CustomException(msg="未配置腾讯云 OCR 密钥，请联系管理员")
    # 图片 URL → 纯 base64（data URI 剥离前缀；公网地址由本站下载兜底）
    data_uri = _resolve_image_data_uri(image_url)
    if data_uri.startswith("data:"):
        image_b64 = data_uri.split(",", 1)[1]
    else:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(data_uri)
                r.raise_for_status()
            import base64 as _b64

            image_b64 = _b64.b64encode(r.content).decode()
        except Exception as e:
            raise CustomException(msg=f"图片获取失败：{e}") from e
    region = settings.TENCENT_OCR_REGION or "ap-guangzhou"
    if card_type == "身份证":
        out = await _idcard_ocr_fields(image_b64, secret_id, secret_key, region)
        return SuccessResponse(data=out, msg="证件识别成功")
    # 医保卡：版式不统一 → 通用印刷体识别 + 关键字段自动提取 + 全文字供医生核对
    try:
        lines = await _tencent_general_ocr(image_b64, secret_id, secret_key, region=region)
    except httpx.HTTPError as e:
        raise CustomException(msg=f"腾讯云 OCR 请求失败：{e}") from e
    except RuntimeError as e:
        raise CustomException(msg=str(e)) from e
    out, ocr_text = _parse_insurance_lines(lines)
    if ocr_text:
        out["ocr_text"] = ocr_text
    if not (out.get("id_number") or out.get("insurance_no") or out.get("patient_name")):
        raise CustomException(msg="未识别到医保卡信息，请正对卡片、光线充足、避免反光后重拍")
    return SuccessResponse(data=out, msg="医保卡识别成功（请核对弹窗文字补充姓名/卡号）")


async def _idcard_ocr_fields(image_b64: str, secret_id: str, secret_key: str, region: str) -> dict:
    """身份证识别并映射为建档字段 key（与前端 fillFromRecognized 兼容）。"""
    try:
        resp_body = await _tencent_idcard_ocr(image_b64, secret_id, secret_key, region=region)
    except httpx.HTTPError as e:
        raise CustomException(msg=f"腾讯云 OCR 请求失败：{e}") from e
    except RuntimeError as e:
        raise CustomException(msg=str(e)) from e
    name = _ocr_text(resp_body, "Name")
    sex = _ocr_text(resp_body, "Sex")
    birth = _ocr_text(resp_body, "Birth")
    id_num = _ocr_text(resp_body, "IdNum")
    out: dict = {}
    if name:
        out["patient_name"] = name
    if sex:
        out["gender"] = sex if sex in ("男", "女") else ("男" if "男" in sex else "女")
    if birth:
        out["birth_date"] = _birth_to_ymd(birth)
    if id_num:
        out["id_number"] = id_num
    if not out:
        raise CustomException(msg="未识别到有效身份证信息，请正对证件、光线充足、避免反光后重拍")
    return out


def _parse_insurance_lines(lines: list[str]) -> tuple[dict, str]:
    """从医保卡通用识别文本中尽力提取：18 位社保号 → id_number、卡号 → insurance_no、姓名 → patient_name。

    返回 (结构化字段, 全部识别文本)。医保卡版式不统一，姓名/卡号无法保证准，交给医生核对。
    """
    import re

    joined = [str(x).strip() for x in lines if str(x).strip()]
    ocr_text = " ".join(joined)[:500]
    out: dict = {}
    # 1) 18 位社会保障号码 / 身份证号
    id18 = ""
    for ln in joined:
        m = re.search(r"(?<!\d)\d{17}[\dXx](?!\d)", ln)
        if m:
            id18 = m.group(0)
            break
    # 2) 卡号：优先 12 位纯数字（社会保障卡卡号），或「卡号/编号」标签后的数字串
    card_no = ""
    for ln in joined:
        if re.fullmatch(r"\d{17}[\dXx]", ln):
            continue
        if re.fullmatch(r"\d{12}", ln):
            card_no = ln
            break
    if not card_no:
        for ln in joined:
            m = re.search(r"(?:卡号|编号|个人编号)\s*[:：]?\s*([A-Z0-9]{8,16})", ln)
            if m:
                card_no = m.group(1)
                break
    # 3) 姓名：仅取「姓名」标签同行后的 1~6 汉字（不跨行猜，防误填）
    name = ""
    for ln in joined:
        m = re.search(r"姓名\s*[:：]?\s*([\u4e00-\u9fa5]{1,6})", ln)
        if m:
            name = m.group(1)
            break
    if id18:
        out["id_number"] = id18
    if card_no:
        out["insurance_no"] = card_no
    if name:
        out["patient_name"] = name
    return out, ocr_text


def _ocr_text(body: dict, key: str) -> str:
    """兼容腾讯 IDCardOCR 两种返回形态：顶层字符串（实测）或 {Content, Confidence}（文档）。"""
    raw = body.get(key) or ""
    if isinstance(raw, dict):
        return ((raw.get("Content") or "").strip() or "")
    return str(raw).strip()


def _birth_to_ymd(value: str) -> str:
    """把身份证出生日期转成 YYYY-MM-DD（兼容 1995年5月13日 / 1995-5-13 等）。"""
    import re

    m = re.match(r"(\d{4})\s*[年./\-]\s*(\d{1,2})\s*[月./\-]\s*(\d{1,2})", value.strip())
    if not m:
        return value.strip()
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


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
    # 兼容 data URL 前缀（data:audio/mp3;base64,xxxx）
    if audio.startswith("data:") and "," in audio:
        audio = audio.split(",", 1)[1]
    try:
        audio_bytes = base64.b64decode(audio)
    except Exception as e:
        raise CustomException(msg="音频数据解码失败，请重新录音") from e
    if not audio_bytes:
        raise CustomException(msg="音频数据为空，请重新录音")
    # 智谱 audio/transcriptions 仅接受真正的文件上传（file 字段）；
    # 以普通表单字段传 base64 会被判为「file和audio参数不能同时为空」(code 1214)
    fmt = (body.get("format") or "mp3").lower().lstrip(".")
    if fmt not in ("mp3", "wav"):
        fmt = "mp3"
    mime = "audio/wav" if fmt == "wav" else "audio/mpeg"
    model = settings.ZHIPU_ASR_MODEL or "glm-asr-2512"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                settings.ZHIPU_BASE_URL.rstrip("/") + "/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.ZHIPU_API_KEY}"},
                files={"file": (f"voice.{fmt}", audio_bytes, mime)},
                data={"model": model},
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
