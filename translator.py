# -*- coding: utf-8 -*-
"""翻译引擎：分块 + 并发 + 缓存 + 多翻译源降级

只翻译英文片段，中文片段原位保留；输出按原顺序拼接，边翻边回传。
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import CACHE_PATH, ensure_dir

log = logging.getLogger("translate")

CHUNK = 800                       # 单次请求字符上限
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
_LATIN_RE = re.compile(r"[A-Za-z]")


class TranslationError(Exception):
    pass


def needs_translation(text):
    """含英文字母才需要翻译（统一译成中文），纯中文不打扰"""
    return bool(_LATIN_RE.search(text or ""))


def english_only(text):
    """提取含英文字母的片段（供朗读：只念英文，中文段丢弃）"""
    parts = [seg for seg, need in _segments(text or "") if need]
    return " ".join(p.strip() for p in parts if p.strip())


def bilingual_text(src, zh):
    """双语对照排版：多行逐行对照（原行下紧跟译行），单行则译文在上、原文在下"""
    src_lines = (src or "").split("\n")
    zh_lines = (zh or "").split("\n")
    if len(src_lines) == 1 and len(zh_lines) == 1:
        return zh + "\n" + src
    out = []
    for i in range(max(len(src_lines), len(zh_lines))):
        s = src_lines[i] if i < len(src_lines) else ""
        z = zh_lines[i] if i < len(zh_lines) else ""
        if s.strip():
            out.append(s)
        if z.strip():
            out.append(z)
    return "\n".join(out)


def _segments(text):
    """按中文/非中文边界切分，返回 [(片段, 是否需要翻译)]"""
    result = []
    for part in re.split(r"([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)", text):
        if not part:
            continue
        need = bool(_LATIN_RE.search(part))
        result.append((part, need))
    return result


def _split_chunks(text, size=CHUNK):
    """先按句切分，再贪心打包成不超过 size 的块；单句超长则硬切"""
    segs = [s for s in re.split(r"(?<=[\n。！？.!?；;])", text) if s]
    chunks, buf = [], ""
    for s in segs:
        while len(s) > size:
            room = size - len(buf)
            if room > 0:
                buf += s[:room]
                chunks.append(buf)
                buf = ""
                s = s[room:]
            else:
                chunks.append(buf)
                buf = ""
        if len(buf) + len(s) > size:
            chunks.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


# ---------------- 缓存 ----------------
class Cache:
    """内存 LRU + 磁盘持久化（重启后仍命中）"""

    def __init__(self, path=CACHE_PATH, maxsize=500):
        self.path = path
        self.maxsize = maxsize
        self.lock = threading.Lock()
        self.data = OrderedDict()
        self._unsaved = 0
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for k, v in items[-self.maxsize:]:
                self.data[k] = v
        except Exception:
            pass

    def _flush(self):
        try:
            ensure_dir()
            items = list(self.data.items())[-self.maxsize:]
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception as e:
            log.debug("缓存写入失败: %s", e)

    def get(self, key):
        with self.lock:
            if key in self.data:
                self.data.move_to_end(key)
                return self.data[key]
        return None

    def put(self, key, value):
        with self.lock:
            self.data[key] = value
            self.data.move_to_end(key)
            while len(self.data) > self.maxsize:
                self.data.popitem(last=False)
            self._unsaved += 1
            if self._unsaved >= 20:
                self._unsaved = 0
                self._flush()
        return value

    def flush(self):
        with self.lock:
            self._flush()


# ---------------- 翻译源 ----------------
class Provider:
    name = "unknown"
    max_chunk = CHUNK          # 该接口单次请求的安全长度

    def translate_chunk(self, text, src="en", dst="zh"):
        raise NotImplementedError


class YoudaoDemo(Provider):
    """有道公开演示接口：免密钥，但可能限流（errorCode 411）"""
    name = "youdao-demo"
    url = "https://aidemo.youdao.com/trans"

    def translate_chunk(self, text, src="en", dst="zh"):
        d = None
        for attempt in range(3):
            try:
                r = requests.post(
                    self.url,
                    data={"q": text, "from": src, "to": "zh-CHS"},
                    headers=UA, timeout=10,
                )
                d = r.json()
            except Exception as e:
                raise TranslationError(f"网络请求失败: {e}") from e
            code = str(d.get("errorCode"))
            if code == "411":            # 频率限制：退避重试
                time.sleep(1.0 * (attempt + 1))
                continue
            if code != "0" or not d.get("translation"):
                raise TranslationError(f"有道接口错误码 {code}")
            return d["translation"][0].strip()
        raise TranslationError("有道接口持续限流，请稍后再试")


class BaiduOfficial(Provider):
    """百度翻译开放平台（需 appid + secret），个人认证有免费额度"""
    name = "baidu"
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def __init__(self, appid, secret):
        self.appid = appid.strip()
        self.secret = secret.strip()

    def translate_chunk(self, text, src="en", dst="zh"):
        salt = str(int(time.time() * 1000))
        sign_src = self.appid + text + salt + self.secret
        sign = hashlib.md5(sign_src.encode("utf-8")).hexdigest()
        params = {
            "q": text, "from": src, "to": dst,
            "appid": self.appid, "salt": salt, "sign": sign,
        }
        last = None
        for attempt in range(3):
            try:
                r = requests.get(self.url, params=params, headers=UA, timeout=10)
                d = r.json()
            except Exception as e:
                raise TranslationError(f"网络请求失败: {e}") from e
            code = str(d.get("error_code", "0"))
            if code in ("52001", "54003"):   # 超时 / 频率限制：重试
                last = f"百度错误码 {code}"
                time.sleep(1.0 * (attempt + 1))
                continue
            if code != "0":
                hint = {
                    "52003": "appid 或密钥不对，或未开通服务",
                    "54001": "签名错误，检查密钥",
                    "54004": "账户余额不足",
                    "58000": "客户端 IP 未授权",
                }.get(code, "请到百度翻译开放平台查看错误码说明")
                raise TranslationError(f"百度错误码 {code}：{hint}")
            rows = d.get("trans_result") or []
            return "\n".join(x.get("dst", "") for x in rows).strip()
        raise TranslationError(last or "百度接口异常")


class MyMemory(Provider):
    """MyMemory 公共接口：免注册、免密钥，匿名每日有字符上限"""
    name = "mymemory"
    max_chunk = 480
    url = "https://api.mymemory.translated.net/get"

    def translate_chunk(self, text, src="en", dst="zh"):
        import html
        last = None
        for _attempt in range(2):
            try:
                r = requests.get(self.url, params={"q": text, "langpair": f"{src}|zh-CN"},
                                 headers=UA, timeout=6)
                d = r.json()
            except Exception as e:
                last = TranslationError(f"MyMemory 网络不可达: {e}")
                time.sleep(0.5)
                continue
            status = d.get("responseStatus")
            if status is not None and str(status) != "200":
                raise TranslationError(f"MyMemory 错误：{d.get('responseDetails') or status}")
            out = html.unescape((d.get("responseData") or {}).get("translatedText") or "").strip()
            if not out:
                last = TranslationError("MyMemory 未返回译文")
                continue
            return out
        raise last or TranslationError("MyMemory 不可用")


class GoogleGtx(Provider):
    """谷歌免费端点，国内需要代理才能访问"""
    name = "google"
    max_chunk = 1500
    url = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, proxy=""):
        self.proxies = {"https": proxy, "http": proxy} if proxy else None

    def translate_chunk(self, text, src="en", dst="zh"):
        try:
            r = requests.get(
                self.url,
                params={"client": "gtx", "sl": src, "tl": "zh-CN", "dt": "t", "q": text},
                headers=UA, timeout=12, proxies=self.proxies,
            )
            data = r.json()
        except Exception as e:
            raise TranslationError(f"谷歌接口不可达（需要代理）: {e}") from e
        try:
            out = "".join(seg[0] for seg in data[0] if seg and seg[0])
        except Exception:
            raise TranslationError("谷歌接口返回格式异常")
        if not out:
            raise TranslationError("谷歌接口未返回译文")
        return out.strip()


# ---------------- 引擎 ----------------
class Translator:
    def __init__(self, cfg, cache=None):
        self.cfg = cfg
        self.cache = cache if cache is not None else Cache()
        self.providers = self._build_providers()

    def _build_providers(self):
        baidu_cfg = self.cfg.get("baidu", {})
        appid = (baidu_cfg.get("appid") or "").strip()
        secret = (baidu_cfg.get("secret") or "").strip()
        baidu = BaiduOfficial(appid, secret) if appid and secret else None
        mode = self.cfg.get("provider", "auto")
        proxy = (self.cfg.get("network", {}).get("proxy") or "").strip()
        google = GoogleGtx(proxy) if proxy else None
        chain = []
        if mode == "baidu":
            if baidu is None:
                log.warning("选择了百度翻译源但未填写 appid/密钥，临时回退到有道演示接口")
                chain = [YoudaoDemo()]
            else:
                chain = [baidu]
        elif mode == "youdao":
            chain = [YoudaoDemo()]
        elif mode == "mymemory":
            chain = [MyMemory()]
        elif mode == "google":
            if google is None:
                log.warning("谷歌接口需要先填写代理地址，临时回退到有道演示接口")
                chain = [YoudaoDemo()]
            else:
                chain = [google]
        else:  # auto：只用免密钥、免注册的接口，有道优先，MyMemory 兜底
            chain = [YoudaoDemo(), MyMemory()]
            if google is not None:
                chain.append(google)
        return chain

    def reload(self):
        self.providers = self._build_providers()

    def _cache_key(self, chunk):
        prov = ",".join(p.name for p in self.providers)
        return hashlib.md5((prov + "\x00en\x00zh\x00" + chunk).encode("utf-8")).hexdigest()

    def _translate_one(self, chunk):
        key = self._cache_key(chunk)
        hit = self.cache.get(key)
        if hit is not None:
            return hit, True
        err = None
        for p in self.providers:
            try:
                out = p.translate_chunk(chunk)
                if out:
                    self.cache.put(key, out)
                    return out, False
            except TranslationError as e:
                err = e
                log.warning("翻译源 %s 失败：%s", p.name, e)
                continue
        raise TranslationError(str(err or "所有翻译源均不可用"))

    def translate(self, text, on_update=None, cancel=None):
        """阻塞执行：逐块并发翻译，按原顺序回传累计结果

        on_update(累计文本) 会在每次有进展时被调用；cancel 为 threading.Event。
        """
        items = _segments(text)
        size = min([p.max_chunk for p in self.providers] or [CHUNK])
        order, values, pending = [], {}, []
        for i, (seg, need) in enumerate(items):
            if not need:
                key = (i, 0)
                order.append(key)
                values[key] = seg            # 中文原样保留
                continue
            for j, ch in enumerate(_split_chunks(seg, size)):
                key = (i, j)
                order.append(key)
                pending.append((key, ch))

        if not pending:
            if on_update:
                on_update("".join(values[k] for k in order))
            return "".join(values[k] for k in order)

        workers = max(1, min(4, int(self.cfg.get("behavior", {}).get("max_workers", 3))))
        acc, pos, errors = "", 0, []

        def emit_ready():
            """按原顺序把已完成块拼接并回传（未完成的块先等着）"""
            nonlocal acc, pos
            progressed = False
            while pos < len(order) and order[pos] in values:
                acc += values[order[pos]]
                pos += 1
                progressed = True
            if progressed and on_update:
                on_update(acc)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._translate_one, ch): key for key, ch in pending}
            for fut in as_completed(futures):
                if cancel is not None and cancel.is_set():
                    for f in futures:
                        f.cancel()
                    return acc
                key = futures[fut]
                try:
                    out, from_cache = fut.result()
                    values[key] = out
                except Exception as e:
                    errors.append(str(e))
                    values[key] = ""         # 占位，保证顺序指针能前进
                emit_ready()
        emit_ready()

        if errors and not acc.strip():
            raise TranslationError(errors[0])
        if errors:
            log.warning("部分片段翻译失败：%s", errors[0])
            if on_update:
                on_update(acc + "\n\n[部分内容翻译失败]")
        return acc


__all__ = [
    "Translator", "TranslationError", "Cache", "needs_translation",
    "english_only", "bilingual_text",
    "BaiduOfficial", "YoudaoDemo", "CHUNK",
]
