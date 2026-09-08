# -*- coding: utf-8 -*-
"""字段级加密（安全加固）。

对病例表的敏感字段（证件号码 id_number / 联系电话 phone / 医保编号 insurance_no）
以及动态表单 form_data 内同名字段做 Fernet 对称加密后落库，读取时自动解密。

- 密钥由 SECRET_KEY 派生（SHA-256 → base64），与现有密码派生方式一致；
- 底层列类型不变（仍是 VARCHAR / JSON），**无需数据库迁移**；
- 兼容存量明文：解密失败（InvalidToken）原样返回，脚本可后续补加密。
"""
import base64
import hashlib
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import JSON, String, TypeDecorator

from app.config.setting import settings

# 需加密的敏感字段名（同时匹配模型列名与 form_data 内键名）
PII_FIELDS = {"id_number", "phone", "insurance_no", "id_card", "mobile"}

_key_material = hashlib.sha256((settings.SECRET_KEY or "dev-secret").encode("utf-8")).digest()
# Fernet 要求 32 字节的 url-safe base64 编码密钥
_FERNET = Fernet(base64.urlsafe_b64encode(_key_material))


def encrypt_value(value: Any) -> Any:
    """加密单个值；空值原样返回。"""
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        value = str(value)
    return _FERNET.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: Any) -> Any:
    """解密单个值；空值或非字符串原样返回；密文损坏（存量明文）原样返回。"""
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return value
    try:
        return _FERNET.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return value


def is_encrypted(value: Any) -> bool:
    """是否已是密文（用于存量脚本判断是否需补加密）。"""
    if not isinstance(value, str) or value == "":
        return False
    try:
        _FERNET.decrypt(value.encode("utf-8"))
        return True
    except (InvalidToken, ValueError):
        return False


def _walk_encrypt(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: (_walk_encrypt(v) if k not in PII_FIELDS else encrypt_value(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_encrypt(i) for i in obj]
    return obj


def _walk_decrypt(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: (_walk_decrypt(v) if k not in PII_FIELDS else decrypt_value(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_decrypt(i) for i in obj]
    return obj


def encrypt_pii_deep(obj: Any) -> Any:
    """幂等深加密：仅对 PII_FIELDS 命中且当前为明文（非密文、非空）的字符串加密；

    已加密值、空值、非字符串值原样返回。用于存量数据补加密脚本，可重复执行。
    """

    if isinstance(obj, dict):
        return {
            k: (
                encrypt_pii_deep(v)
                if k not in PII_FIELDS
                else (encrypt_value(v) if (isinstance(v, str) and not is_encrypted(v)) else v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [encrypt_pii_deep(i) for i in obj]
    return obj


class EncryptedString(TypeDecorator):
    """透明加密字符串列：写入加密、读取解密。底层仍是 VARCHAR，无需迁移。"""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return encrypt_value(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        return decrypt_value(value)


class EncryptedJson(TypeDecorator):
    """透明加密 JSON 列：仅对 PII_FIELDS 命中的键加密其值，其余原样。底层仍是 JSON。"""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        return _walk_encrypt(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        return _walk_decrypt(value)
