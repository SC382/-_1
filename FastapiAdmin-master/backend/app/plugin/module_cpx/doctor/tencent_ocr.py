# -*- coding: utf-8 -*-
"""腾讯云文字识别 OCR 调用封装（TC3-HMAC-SHA256 签名，纯标准库 + httpx，无第三方云 SDK 依赖）。

供胸痛中心证件扫描使用：身份证识别 IDCardOCR（Version 2018-11-19）。
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


async def idcard_ocr(
    image_base64: str,
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    card_side: str = "FRONT",
    timeout: float = 30,
) -> dict:
    """调用腾讯云 IDCardOCR 识别身份证单面。

    入参 image_base64 为纯 base64（不含 data: 前缀）；card_side 默认 FRONT（人像面）。
    返回腾讯云响应中的 Response 体（字段为 {Content, Confidence} 结构）。
    失败抛 RuntimeError（含腾讯返回的业务错误码与信息）。
    """
    payload = '{"ImageBase64":%s,"CardSide":%s}' % (
        _json_str(image_base64),
        _json_str(card_side),
    )
    ts = int(datetime.now().timestamp())
    date = _utc_date(ts)
    service = "ocr"
    algorithm = "TC3-HMAC-SHA256"

    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_headers = (
        "content-type:application/json; charset=utf-8\n"
        f"host:{OCR_HOST}\n"
        "x-tc-action:idcardocr\n"
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
        "X-TC-Action": "IDCardOCR",
        "X-TC-Version": OCR_VERSION,
        "X-TC-Timestamp": str(ts),
        "X-TC-Region": region,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"https://{OCR_HOST}/", headers=headers, content=payload
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


def _json_str(value: str) -> str:
    """把字符串安全放进 JSON 字面量（避免手拼引号转义问题）。"""
    import json

    return json.dumps(value, ensure_ascii=False)
