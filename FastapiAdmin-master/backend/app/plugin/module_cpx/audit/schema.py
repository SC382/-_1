# -*- coding: utf-8 -*-
"""病例审核 Schema"""

from pydantic import BaseModel, Field


class AuditApproveSchema(BaseModel):
    """审核通过"""
    case_id: int = Field(..., description="病例ID")
    audit_comment: str | None = Field(default=None, max_length=500, description="审核意见")


class AuditRejectSchema(BaseModel):
    """审核驳回（驳回原因必填）"""
    case_id: int = Field(..., description="病例ID")
    audit_comment: str = Field(..., min_length=1, max_length=500, description="驳回原因")


class AuditRecordUpdateSchema(BaseModel):
    """修改审核记录"""
    audit_result: str = Field(..., description="审核结果 pass/reject")
    audit_comment: str | None = Field(default=None, max_length=500, description="审核意见/驳回原因")
