# -*- coding: utf-8 -*-
"""导入胸痛中心认证标准 PDF 到 AI 知识库分片表 ai_kb_chunk。

用法：ENVIRONMENT=dev .venv/Scripts/python.exe scripts/import_kb_pdf.py
可重复执行：每次先清空旧分片再重建（保持与源文件一致）。
"""
import os
import re
import sys

import pymysql
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FILES = [
    r"C:\Users\张鹏伟\Desktop\中国胸痛中心再认证标准（标准版）(1).pdf",
    r"C:\Users\张鹏伟\Desktop\中国胸痛中心认证标准（第六版）.pdf",
]

MIN_CHUNK = 80      # 分片最短字符数（太短丢弃）
MAX_CHUNK = 900     # 分片目标最大字符数（超出按句切分）
OVERLAP = 0         # 分片重叠（简单模式不重叠）


def extract_text(path: str) -> list[tuple[int, str]]:
    """返回 [(页码, 文本)]，过滤空白页。"""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        txt = re.sub(r"[ \t\u3000]+", " ", txt)          # 压缩空白
        txt = re.sub(r"\n{3,}", "\n\n", txt)              # 压缩多余空行
        if len(txt) >= MIN_CHUNK:
            pages.append((i, txt))
    return pages


def split_paragraph(text: str) -> list[str]:
    """合并 PDF 提取的逐行硬换行，按真实段落（空行）切分；长段按句号滑窗。"""
    # pypdf 提取的文本：每行一个 \n，段落间有空行 \n\n。
    # 先把段落分隔符标记出来，再合并行，避免把一行当一段。
    text = text.replace("\n\n", "\u0001")
    text = text.replace("\n", "")
    paras = [p.strip() for p in text.split("\u0001") if p.strip()]
    chunks = []
    for p in paras:
        if len(p) <= MAX_CHUNK:
            chunks.append(p)
            continue
        # 长段落按中文句号/分号滑窗切
        segs = [s.strip() for s in re.split(r"(?<=[。；;])", p) if s.strip()]
        buf = ""
        for seg in segs:
            if buf and len(buf) + len(seg) > MAX_CHUNK:
                chunks.append(buf)
                buf = seg
            else:
                buf += seg
        if buf:
            chunks.append(buf)
    return chunks


def main() -> None:
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password="123456",
                           database="fastapiadmin", charset="utf8mb4")
    cur = conn.cursor()
    # 先清空旧分片（重建）
    cur.execute("DELETE FROM ai_kb_chunk")
    conn.commit()

    total = 0
    for path in FILES:
        if not os.path.exists(path):
            print(f"[跳过] 文件不存在: {path}")
            continue
        fname = os.path.basename(path)
        pages = extract_text(path)
        idx = 0
        for page_no, text in pages:
            for chunk in split_paragraph(text):
                if len(chunk) < MIN_CHUNK:
                    continue
                idx += 1
                cur.execute(
                    "INSERT INTO ai_kb_chunk (source_file, page_no, chunk_index, content) VALUES (%s,%s,%s,%s)",
                    (fname, page_no, idx, chunk),
                )
                total += 1
        print(f"[OK] {fname}: {len(pages)} 页, {idx} 个分片")
    conn.commit()
    cur.execute("SELECT source_file, COUNT(*) FROM ai_kb_chunk GROUP BY source_file")
    print("=== 入库统计 ===")
    for r in cur.fetchall():
        print(" ", r)
    print(f"总计 {total} 分片")
    conn.close()


if __name__ == "__main__":
    main()
