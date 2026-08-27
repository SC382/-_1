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
        # 图片识别：调用通义千问 Vision 模型
        prompt = (
            "你是一个严格的医疗文字识别助手。请仔细阅读这张图片中的所有文字。\n\n"
            "规则（必须严格遵守）：\n"
            "1. **只提取图片中明确可见、清晰可读的文字信息**，绝对不要编造、推测或补充任何图片中没有的内容\n"
            "2. 如果某个字段在图片中找不到对应的文字，该字段必须返回空字符串\"\"\n"
            "3. 如果图片中完全没有任何可识别的患者信息，所有字段都返回空字符串\n"
            "4. 提取的内容必须与图片文字**完全一致**，不要修改、润色或重新组织\n\n"
            "请提取以下字段（找不到就返回\"\"）：\n"
            "- patient_name：患者姓名（图片中写的什么就是什么）\n"
            "- gender：性别（男/女）\n"
            "- age：年龄（图片中写的数字）\n"
            "- phone：电话号码（图片中写的手机号）\n"
            "- come_type：来院方式（120/自行/转诊）\n"
            "- onset_address：发病地址（图片中写的地址）\n"
            "- id_type：证件类型（身份证/社保卡/其他）\n\n"
            "只返回纯JSON对象，不要包含任何解释、标注或markdown格式。"
        )
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": prompt},
        ]}]
        model = settings.OPENAI_VISION_MODEL or "qwen-vl-plus"
    else:
        # 文字解析：调用通义千问对话模型
        prompt = (
            "你是医疗信息提取助手。从以下文字中提取患者基本信息，"
            "只返回JSON（无解释无markdown）：patient_name, gender, age, phone, come_type, onset_address, id_type。"
            "未出现的字段留空字符串。\n\n" + text
        )
        messages = [{"role": "user", "content": prompt}]
        model = settings.OPENAI_MODEL or "qwen-plus"

    if not settings.OPENAI_API_KEY:
        raise CustomException(msg="未配置 AI API Key")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                settings.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 1000, "temperature": 0.1},
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
        for f in ["patient_name", "gender", "age", "phone", "come_type", "onset_address", "id_type"]:
            result.setdefault(f, "")
        return SuccessResponse(data=result, msg="AI 识别成功")
    except json.JSONDecodeError:
        return SuccessResponse(data={"raw_text": content}, msg="AI 返回文本（请核对）")


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
