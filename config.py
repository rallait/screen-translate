# -*- coding: utf-8 -*-
"""配置与路径：所有用户数据集中在 %APPDATA%\\hxy-translate 下"""
import copy
import json
import os

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "hxy-translate")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LOG_PATH = os.path.join(APP_DIR, "app.log")
CACHE_PATH = os.path.join(APP_DIR, "cache.json")

DEFAULTS = {
    # auto=有道演示 + MyMemory 兜底（全部免密钥）；可选 youdao / mymemory / google / baidu
    "provider": "auto",
    "baidu": {"appid": "", "secret": ""},
    "network": {"proxy": ""},   # 例如 http://127.0.0.1:7897；仅谷歌接口会用到
    "ui": {
        "font_size": 11,
        "max_result_height": 460,
        "icon_size": 34,
        "theme": "midnight",            # midnight / obsidian / aurora / glass / sakura
        "bilingual": True,              # 双语对照：译文下方附英文原文
    },
    "behavior": {
        "drag_enabled": True,
        "drag_threshold": 25,
        "hotkey_quit": "ctrl+alt+q",
        "hotkey_ocr": "ctrl+alt+s",
        "max_workers": 3,
        "clipboard_restore": True,
    },
    "autostart": False,
}


def ensure_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def _merge(base, override):
    """把 override 合进 base，缺失项保持默认值（容忍手工改坏配置文件）"""
    out = copy.deepcopy(base)
    if not isinstance(override, dict):
        return out
    for k, v in override.items():
        if isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    ensure_dir()
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = _merge(cfg, json.load(f))
    except FileNotFoundError:
        save(cfg)
    except Exception:
        # 配置损坏时用默认值，不阻塞启动
        pass
    return cfg


def save(cfg):
    ensure_dir()
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def get(cfg, section, key, default=None):
    try:
        return cfg[section][key]
    except Exception:
        return default
