# -*- coding: utf-8 -*-
"""AI 助手知识库问答：基于胸痛中心认证标准 PDF 分片检索 + DeepSeek 回答 + 来源标注。"""
from collections import Counter

import httpx
import jieba
from sqlalchemy import select

from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.plugin.module_cpx.models import AiKbChunkModel

# 检索停用词（问句常见虚词）
_STOPWORDS = set(
    "的了是在有和与或及为对从把被这那之以及等中上下到进行通过应该需要可以如果则请吗呢啊吧"
    "什么如何怎么多少哪些为何为什么怎样一个哪些一些请问根据按照关于请问一下帮忙说说回答解释"
)

# 医学指标缩写 → 中文表述别名（PDF 原文多使用中文，不用缩写）
_TERM_ALIASES: dict[str, list[str]] = {
    "D2W": ["进门至球囊", "进门到球囊", "球囊开通", "door to balloon"],
    "FMC2ECG": ["首次医疗接触", "首份心电图", "第一份心电图"],
    "FMC2W": ["首次医疗接触到导丝", "导丝通过"],
    "D2N": ["进门至溶栓", "开始溶栓"],
    "S2FMC": ["呼叫", "首次医疗接触"],
    "DIDO": ["入门到出门", "door in door out"],
    "FMC2B": ["首次医疗接触到球囊"],
    "PPCI": ["直接PCI", "急诊PCI", "直接经皮"],
    "STEMI": ["急性ST段抬高", "st段抬高型"],
    "NSTEMI": ["急性非ST段抬高", "非st段抬高"],
}


def _tokenize(text: str) -> list[str]:
    """jieba 分词并过滤停用词与单字。"""
    words = []
    for w in jieba.lcut(text):
        w = w.strip()
        if len(w) >= 2 and w not in _STOPWORDS and not w.isdigit():
            words.append(w)
    return words


class KbService:
    def __init__(self, auth: AuthSchema | None = None) -> None:
        self.auth = auth

    async def _search(self, question: str, top_n: int = 5) -> list[tuple[int, AiKbChunkModel]]:
        """关键词检索：对每个分片统计问题关键词出现次数，取 top-N。

        支持医学缩写别名扩展（如 D2W → 进门至球囊/球囊开通），提高召回。
        """
        kws = _tokenize(question)
        if not kws:
            return []
        # 缩写别名扩展：命中则追加中文表述，提高对 PDF 原文的召回
        expanded = list(kws)
        for kw in kws:
            for alias in _TERM_ALIASES.get(kw.upper(), []):
                expanded.append(alias)
        async with async_db_session() as db:
            rows = (await db.execute(select(AiKbChunkModel))).scalars().all()
        scored: list[tuple[int, AiKbChunkModel]] = []
        for r in rows:
            s = sum(r.content.count(kw) for kw in expanded)
            if s > 0:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_n]

    async def _llm(self, question: str, context: str) -> str:
        """调用 DeepSeek（OPENAI 兼容）基于知识库片段回答。

        优先使用 DEEPSEEK_* 配置（问答走 DeepSeek）；未配置时回退 OPENAI_*（千问）。
        图片识别不受影响（仍走 OPENAI_VISION_MODEL 千问）。
        """
        api_key = settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY
        if not api_key or api_key.startswith("sk-placeholder"):
            raise CustomException(msg="未配置大模型 API Key（请在 env/.env.dev 配置 DEEPSEEK_API_KEY）")
        base_url = settings.DEEPSEEK_BASE_URL or settings.OPENAI_BASE_URL
        model = settings.DEEPSEEK_MODEL or settings.OPENAI_KB_MODEL or settings.OPENAI_MODEL
        prompt = (
            "你是胸痛中心认证标准知识库助手。请严格根据以下参考资料回答用户问题，"
            "不要编造资料之外的内容；若资料不足以回答，请明确回复“知识库中未找到相关内容”。\n\n"
            "参考资料：\n"
            f"{context}\n\n"
            f"用户问题：{question}\n\n"
            "要求：\n"
            "1. 用中文分条回答，突出关键点（如数值、时限、要求）；\n"
            "2. 资料中时间指标多为中文表述（如“进门至球囊开通”对应 D2W、“首次医疗接触至首份心电图”对应 FMC2ECG），"
            "请先对应术语再回答，不要把“资料中未出现缩写”误判为“资料未涉及”；\n"
            "3. 回答末尾单独一行标注依据来源，格式：【依据：《文件名》（第X页）】，引用多个文件用顿号分隔。"
        )
        try:
            _url = base_url.rstrip("/") + "/chat/completions"
            _headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            # 关闭思考：DEEPSEEK_MODEL（deepseek-v4-flash）是推理模型，思考草稿会挤占 max_tokens
            # （实测同一问题思考占约 1000 tokens），截断后回答缺尾且无任何报错；
            # 关闭后约 1s 返回完整回答，网关不认该参数（400）时去掉重试一次
            _body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.2,
                "thinking": {"type": "disabled"},
            }
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(_url, headers=_headers, json=_body)
                if resp.status_code == 400:
                    _body.pop("thinking", None)
                    resp = await client.post(_url, headers=_headers, json=_body)
                resp.raise_for_status()
                data = resp.json()
            msg = ((data.get("choices") or [{}])[0].get("message") or {})
            content = (msg.get("content") or "").strip()
            # 推理型模型（deepseek-v4-flash）思考草稿在 reasoning_content，正文在 content；
            # 只有 content 为空且 reasoning 明显是最终结论时才兜底，否则不要把思考过程当回答返回
            if not content:
                reason = (msg.get("reasoning_content") or "").strip()
                if reason and any(kw in reason for kw in ("【依据", "知识库中未找到", "综上所述", "回答：", "最终")):
                    content = reason
            if not content:
                raise CustomException(msg="AI 模型未返回有效回答，请稍后重试")
            return content
        except CustomException:
            raise
        except Exception as e:  # noqa: BLE001
            raise CustomException(msg=f"AI 服务调用失败：{e}") from e

    async def ask(self, question: str) -> dict:
        hits = await self._search(question)
        if not hits:
            return {
                "answer": "知识库中未找到相关内容，请换一种问法，或确认问题与胸痛中心认证标准相关。",
                "sources": [],
                "hit_count": 0,
            }
        context = "\n\n".join(
            f"【来源：《{r.source_file}》第{r.page_no}页】\n{r.content}" for _, r in hits
        )
        answer = await self._llm(question, context)
        # 结构化来源（去重：同文件同页合并）
        seen: set[tuple[str, int]] = set()
        sources: list[dict] = []
        for _, r in hits:
            key = (r.source_file, r.page_no)
            if key not in seen:
                seen.add(key)
                sources.append({"source_file": r.source_file, "page_no": r.page_no})
        return {"answer": answer, "sources": sources, "hit_count": len(hits)}

    async def status(self) -> dict:
        async with async_db_session() as db:
            rows = (await db.execute(select(AiKbChunkModel))).scalars().all()
        cnt = Counter(r.source_file for r in rows)
        return {
            "total": len(rows),
            "files": [{"file": k, "chunks": v} for k, v in cnt.items()],
        }
