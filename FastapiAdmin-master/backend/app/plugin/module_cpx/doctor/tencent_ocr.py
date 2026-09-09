# -*- coding: utf-8 -*-
"""腾讯云文字识别 OCR 调用封装（TC3-HMAC-SHA256 签名，纯标准库 + httpx，无第三方云 SDK 依赖）。

供胸痛中心证件扫描使用：
- idcard_ocr：身份证识别 IDCardOCR（Version 2018-11-19）
- general_ocr：通用印刷体识别 GeneralBasicOCR（医保卡等无专用接口的卡片）

注意：腾讯云 OCR 接口仅支持主账号 SecretId/SecretKey 调用。
"""
import hashlib
import hmac
from datetime import datetime, timezone

import httpx

OCR_HOST = "ocr.tencentcloudapi.com"
OCR_VERSION = "2018-11-19"


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _utc_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


async def _tc3_post(
    action: str,
    payload: dict,
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    timeout: float = 30,
) -> dict:
    """腾讯云 TC3-HMAC-SHA256 签名 POST（JSON）。失败抛 RuntimeError（含腾讯业务错误码）。"""
    import json

    body_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    ts = int(datetime.now().timestamp())
    date = _utc_date(ts)
    service = "ocr"
    algorithm = "TC3-HMAC-SHA256"
    action_lower = action.lower()

    hashed_payload = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
    canonical_headers = (
        "content-type:application/json; charset=utf-8\n"
        f"host:{OCR_HOST}\n"
        f"x-tc-action:{action_lower}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = "POST\n/\n\n" + canonical_headers + "\n" + signed_headers + "\n" + hashed_payload

    scope = f"{date}/{service}/tc3_request"
    string_to_sign = (
        f"{algorithm}\n{ts}\n{scope}\n"
        + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    )

    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        f"{algorithm} Credential={secret_id}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": OCR_HOST,
        "X-TC-Action": action,
        "X-TC-Version": OCR_VERSION,
        "X-TC-Timestamp": str(ts),
        "X-TC-Region": region,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"https://{OCR_HOST}/", headers=headers, content=body_str
        )
        resp.raise_for_status()
        data = resp.json()

    body = data.get("Response") or {}
    err = body.get("Error")
    if err:
        raise RuntimeError(
            f"腾讯云 OCR 调用失败 {err.get('Code')}: {err.get('Message')}"
        )
    return body


async def idcard_ocr(
    image_base64: str,
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    card_side: str = "FRONT",
    timeout: float = 30,
) -> dict:
    """调用腾讯云 IDCardOCR 识别身份证单面。

    image_base64 为纯 base64（不含 data: 前缀）；card_side 默认 FRONT（人像面）。
    返回腾讯云 Response 体（实测字段为顶层字符串，文档形态为 {Content, Confidence}）。
    """
    return await _tc3_post(
        "IDCardOCR",
        {"ImageBase64": image_base64, "CardSide": card_side},
        secret_id,
        secret_key,
        region=region,
        timeout=timeout,
    )


async def general_ocr(
    image_base64: str,
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    timeout: float = 30,
) -> list[str]:
    """调用腾讯云 GeneralBasicOCR 通用印刷体识别，返回识别出的文本行列表（按识别顺序）。"""
    body = await _tc3_post(
        "GeneralBasicOCR",
        {"ImageBase64": image_base64},
        secret_id,
        secret_key,
        region=region,
        timeout=timeout,
    )
    items = body.get("DetectedTexts") or []
    return [str(i.get("DetectedText", "")).strip() for i in items if i.get("DetectedText")]
