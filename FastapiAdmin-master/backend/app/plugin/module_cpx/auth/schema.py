# -*- coding: utf-8 -*-
"""业务认证接口 Schema"""

from pydantic import BaseModel, Field


class LoginSchema(BaseModel):
    """登录参数"""
    username: str = Field(..., description="登录账号")
    password: str = Field(..., description="密码")
