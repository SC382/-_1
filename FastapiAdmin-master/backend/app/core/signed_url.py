# -*- coding: utf-8 -*-
"""静态资源签名 URL（安全加固）。

背景：/static 下存放患者照片、心电图、病历 PDF、会议材料等隐私文件，
此前通过 StaticFiles 无鉴权挂载，任何拿到 URL 的人都能直接下载。
现改为「签名 URL」：URL 中带 exp（过期时间戳）与 sign（HMAC-SHA256 签名），
只有签名校验通过才允许读取文件；未签名或过期的请求返回 403。

前端无需改造：URL 由后端生成并返回，已自带签名，
<img src> / <image src> 这类不带 Authorization 头的标签也能正常加载。
"""
import hashlib
import hmac
import time
from urllib.parse import quote, urlencode

from app.config.setting import settings

# 签名默认有效期：24 小时（兼顾浏览器/App 图片缓存与链接泄露风险）
DEFAULT_TTL = 24 * 60 * 60
# 签名截取长度（Hex 前 32 位，已足够安全且缩短 URL）
_SIGN_LEN = 32


def normalize_static_path(path: str) -> str:
    """归一化为 STATIC_DIR 内的相对路径。

    支持三种入参形式：
    - /api/v1/static/uploads/doctor/a.jpg（带 ROOT_PATH + STATIC_URL）
    - /static/uploads/doctor/a.jpg（带 STATIC_URL）
    - uploads/doctor/a.jpg（相对路径）
    """
    if not path:
        return ""
    p = path.split("?", 1)[0]
    prefixes = [
        f"{settings.ROOT_PATH}{settings.STATIC_URL}/".replace("//", "/"),
        f"{settings.STATIC_URL}/",
    ]
    for prefix in prefixes:
        if p.startswith(prefix):
            p = p[len(prefix):]
            break
    return p.lstrip("/")


def _signature(rel_path: str, exp: int) -> str:
    """基于 SECRET_KEY 对「相对路径|过期时间」做 HMAC-SHA256。"""
    msg = f"{rel_path}|{exp}".encode("utf-8")
    key = (settings.SECRET_KEY or "").encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:_SIGN_LEN]


def sign_static_url(url_or_path: str, ttl: int = DEFAULT_TTL) -> str:
    """给静态资源路径/完整 URL 追加 exp + sign 查询参数。

    非本项目静态资源（如 http(s) 外链、data: 内联图）原样返回，不改写。
    """
    if not url_or_path:
        return url_or_path
    rel = normalize_static_path(url_or_path)
    # 外链或 data URI：不处理
    if not rel or url_or_path.startswith("data:"):
        return url_or_path
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        # 仅对指向本后端静态目录的 URL 签名，其他外链原样返回
        prefix = f"{settings.ROOT_PATH}{settings.STATIC_URL}/".replace("//", "/")
        if f"/{settings.STATIC_URL.strip('/')}/" not in url_or_path:
            return url_or_path
        exp = int(time.time()) + ttl
        sign = _signature(rel, exp)
        sep = "&" if "?" in url_or_path else "?"
        return f"{url_or_path}{sep}{urlencode({'exp': exp, 'sign': sign})}"
    # 相对路径：补全为 /api/v1/static/... 并签名
    exp = int(time.time()) + ttl
    sign = _signature(rel, exp)
    base = f"{settings.ROOT_PATH}{settings.STATIC_URL}/{quote(rel)}".replace("//", "/")
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode({'exp': exp, 'sign': sign})}"


def verify_static_signature(rel_path: str, exp: str | int, sign: str) -> bool:
    """校验静态资源签名：未过期且签名一致才放行。"""
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if not sign or not rel_path:
        return False
    if exp_int < int(time.time()):
        return False  # 已过期
    expected = _signature(rel_path, exp_int)
    return hmac.compare_digest(expected, str(sign))
