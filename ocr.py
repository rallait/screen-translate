# -*- coding: utf-8 -*-
"""OCR 截图取词

优先 rapidocr（若已安装），否则回退到 Windows 自带 OCR（无需安装任何东西）。
"""
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading

log = logging.getLogger("ocr")

_engine = None
_lock = threading.Lock()
_PS1_NAMES = ("ocr_winrt.ps1",)


def _find_ps1():
    """优先同目录，其次 exe 所在目录（打包后两种布局都能找到）"""
    base_dirs = [os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(os.path.abspath(sys.executable))]
    for base in base_dirs:
        for name in _PS1_NAMES:
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
    return None


_PS1 = _find_ps1()
_CJK_GAP = re.compile(r"([\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")


def _has_rapidocr():
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _get_rapidocr():
    global _engine
    with _lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            log.info("初始化 rapidocr 引擎")
            _engine = RapidOCR()
        return _engine


def _normalize(text):
    """Windows OCR 会在中文字之间插空格，这里去掉"""
    prev = None
    while prev != text:
        prev = text
        text = _CJK_GAP.sub(r"\1", text)
    return text


def available():
    return _has_rapidocr() or os.path.exists(_PS1)


def image_to_text(pil_image):
    """PIL 图片 -> 文本；失败抛 RuntimeError"""
    if _has_rapidocr():
        try:
            import numpy as np
            engine = _get_rapidocr()
            arr = np.array(pil_image.convert("RGB"))[:, :, ::-1]
            result, _ = engine(arr)
            if result:
                return "\n".join(r[1] for r in result if len(r) > 1 and r[1]).strip()
            return ""
        except Exception as e:
            log.warning("rapidocr 失败，回退系统 OCR：%s", e)

    if not os.path.exists(_PS1):
        raise RuntimeError("系统 OCR 脚本缺失且未安装 rapidocr")

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        pil_image.convert("RGB").save(path, "PNG")
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0      # SW_HIDE
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _PS1, "-Path", path],
            capture_output=True, text=True, encoding="utf-8", timeout=25,
            creationflags=0x08000000,  # CREATE_NO_WINDOW，避免闪黑框
            startupinfo=si,
        )
        if proc.returncode == 2:
            raise RuntimeError("系统缺少 OCR 语言包，请在 设置 → 时间和语言 → 语言 中安装中文/英文")
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or "系统 OCR 调用失败").strip()[:200])
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        return _normalize("\n".join(lines))
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
