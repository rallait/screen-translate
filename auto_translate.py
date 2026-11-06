# -*- coding: utf-8 -*-
"""划词翻译 v2 —— 拖选即翻译 + 截图取词

用法：
  拖选英文 → 鼠标移到「译」图标上 → 显示译文（可用「复制」按钮复制）
  截图翻译：Ctrl + Alt + S，拖框选择区域
  退出：Ctrl + Alt + Q 或托盘右键
设置：托盘右键 → 设置…（翻译源、快捷键、开机自启、字号）
"""
import argparse
import ctypes
import json
import logging
import os
import queue
import sys
import threading
import time
from logging.handlers import RotatingFileHandler


def hide_console():
    """仅当控制台是本进程独享时（直接双击 .py 新建的）才隐藏；
    从终端里启动时控制台还挂着父 shell，绝不能动。
    放在重依赖导入之前调用，尽量缩短黑窗口闪现时间"""
    try:
        from ctypes import wintypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            return
        arr = (wintypes.DWORD * 8)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(arr, 8)
        if count <= 1:                       # 只有本进程附着：这是双击生成的黑窗口
            ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
    except Exception:
        pass


hide_console()

import keyboard
import pyperclip
import tkinter as tk
from pynput import mouse

import config as cfgmod
import ocr
import tts
import ui
from translator import Cache, TranslationError, Translator, english_only, needs_translation

SCRIPT = os.path.abspath(__file__)
__version__ = "1.0.0"
MAX_TEXT = 10000                      # 单次划词翻译上限，防止超大文本卡死
MUTEX_NAME = "Global\\hxy_translate_single"
task_queue = queue.Queue()            # 线程 -> Tk 主线程 的安全通道

log = logging.getLogger("app")


def setup_logging():
    cfgmod.ensure_dir()
    handler = RotatingFileHandler(cfgmod.LOG_PATH, maxBytes=1024 * 1024, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if sys.stderr is not None:          # 打包成无控制台程序时 stderr 为 None
        root.addHandler(logging.StreamHandler(sys.stderr))
    try:                                # 硬崩溃（段错误等）也留痕，pythonw 下无控制台也能查
        import faulthandler
        faulthandler.enable(open(os.path.join(cfgmod.APP_DIR, "crash.log"), "a",
                                 encoding="utf-8"))
    except Exception:
        pass
    log.info("启动：python=%s", sys.executable)


def single_instance():
    """已有一个实例在跑就静默退出"""
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
            return None
        return handle
    except Exception:
        return None


# ---------------- 开机自启 ----------------
def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{SCRIPT}"'


def set_autostart(enable):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    name = "HXY划词翻译"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, launch_command())
                log.info("已开启开机自启")
            else:
                try:
                    winreg.DeleteValue(k, name)
                    log.info("已关闭开机自启")
                except FileNotFoundError:
                    pass
    except Exception as e:
        log.warning("设置开机自启失败：%s", e)


# ---------------- 主程序 ----------------
class App:
    def __init__(self, cfg, selftest=False):
        self.cfg = cfg
        self.selftest = selftest
        self.cache = Cache()
        self.translator = Translator(cfg, self.cache)
        self.cancel_event = threading.Event()
        self.pending = None            # (x, y, text) 等待触发的划词
        self.overlay = None
        self.settings_win = None
        self.tray = None
        self._hook_ids = []
        self._press_pos = None
        self._listener = None

        self.root = tk.Tk()
        self.root.withdraw()
        ui.set_theme(cfg.get("ui", {}).get("theme", ui.DEFAULT_THEME))
        ui.apply_theme(self.root)
        self._build_windows()

    def _build_windows(self):
        u = self.cfg["ui"]
        self.icon = ui.IconWindow(self.root, size=int(u.get("icon_size", 34)),
                                  on_trigger=self._on_icon_hover,
                                  on_theme=self._set_theme)
        self.result = ui.ResultWindow(self.root, font_size=int(u.get("font_size", 11)),
                                      max_height=int(u.get("max_result_height", 460)),
                                      on_speak=self._on_speak,
                                      on_theme=self._set_theme,
                                      bilingual=bool(u.get("bilingual", True)))
        # 朗读：Windows 自带语音，念完回到「朗读」
        self.speaker = tts.Speaker(on_finish=lambda: task_queue.put(("tts_state", False)))

    def _on_speak(self, text):
        """text 为空表示停止；朗读一律念英文（取本轮原文中的英文片段）"""
        if text:
            en = english_only(self.result.src_text) or english_only(text) or text
            ok = self.speaker.speak(en)
            self.result.set_speaking(ok)
        else:
            self.speaker.stop()
            self.result.set_speaking(False)

    # ---- 生命周期 ----
    def start(self):
        if not self.selftest:
            self._register_hotkeys()
            self._start_mouse_listener()
            self._start_tray()
        self.root.after(40, self._poll)

    def run(self):
        self.start()
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        log.info("退出")
        self.cancel_event.set()
        try:
            self.speaker.stop()
        except Exception:
            pass
        try:
            if self._listener:
                self._listener.stop()
            keyboard.unhook_all()
        except Exception:
            pass
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.cache.flush()
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---- 快捷键 ----
    def _register_hotkeys(self):
        bh = self.cfg["behavior"]
        for hk, action in ((bh.get("hotkey_quit", "ctrl+alt+q"), "quit"),
                           (bh.get("hotkey_ocr", "ctrl+alt+s"), "ocr")):
            try:
                self._hook_ids.append(keyboard.add_hotkey(hk, lambda a=action: task_queue.put((a, None))))
                log.info("已注册快捷键 %s -> %s", hk, action)
            except Exception as e:
                log.warning("快捷键 %s 注册失败：%s", hk, e)
        keyboard.on_press_key("esc", lambda e: task_queue.put(("esc", None)))

    def _unregister_hotkeys(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._hook_ids = []

    # ---- 鼠标拖选监听 ----
    def _start_mouse_listener(self):
        def on_click(x, y, button, pressed):
            try:
                self._on_click(x, y, button, pressed)
            except Exception as e:
                log.exception("鼠标回调异常：%s", e)

        self._listener = mouse.Listener(on_click=on_click)
        self._listener.daemon = True
        self._listener.start()

    def _inside_own_windows(self, x, y):
        for b in (self.icon.bounds(), self.result.bounds()):
            if b and b[0] <= x <= b[2] and b[1] <= y <= b[3]:
                return True
        return False

    def _on_click(self, x, y, button, pressed):
        if button != mouse.Button.left:
            return
        if pressed:
            self._press_pos = (x, y)
            if not self._inside_own_windows(x, y):
                task_queue.put(("dismiss", None))
            return
        if self._press_pos is None:
            return
        sx, sy = self._press_pos
        self._press_pos = None
        if self._inside_own_windows(sx, sy) or self._inside_own_windows(x, y):
            return                      # 在自己窗口里选择译文，别再触发
        if not self.cfg["behavior"].get("drag_enabled", True):
            return
        threshold = float(self.cfg["behavior"].get("drag_threshold", 25))
        if (x - sx) ** 2 + (y - sy) ** 2 >= threshold ** 2:
            threading.Thread(target=self._copy_worker, args=(x, y), daemon=True).start()

    # ---- 取词（并还原剪贴板）----
    def _copy_worker(self, x, y):
        text = self._read_selection()
        if not text:
            return
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT]
        if needs_translation(text):
            task_queue.put(("icon", (x, y, text)))

    def _read_selection(self):
        """模拟 Ctrl+C 取选中文字；无论成功与否都恢复原剪贴板内容"""
        prev = ""
        try:
            prev = pyperclip.paste() or ""
        except Exception:
            pass
        token = "\u200bhxy-%d" % int(time.time() * 1000)
        try:
            pyperclip.copy(token)
        except Exception:
            token = None
        try:
            keyboard.send("ctrl+c")
            deadline = time.time() + 0.8
            while time.time() < deadline:
                time.sleep(0.05)
                try:
                    cur = pyperclip.paste() or ""
                except Exception:
                    cur = ""
                if token is None or cur != token:
                    text = cur.strip()
                    return text if text else ""
            log.debug("未检测到新的选中内容")
            return ""
        except Exception as e:
            log.warning("取词失败：%s", e)
            return ""
        finally:
            if self.cfg["behavior"].get("clipboard_restore", True):
                try:
                    pyperclip.copy(prev)
                except Exception:
                    pass

    # ---- 翻译流程 ----
    def _on_icon_hover(self):
        if not self.pending:
            return
        task_queue.put(("translate", self.pending))

    def _start_translate(self, x, y, text):
        self.cancel_event.set()                 # 取消上一轮
        self.cancel_event = threading.Event()
        cancel = self.cancel_event
        if self.speaker.speaking():
            self._on_speak("")                  # 换内容前先停止朗读
        self.icon.hide()
        self.pending = None
        if self.translator.providers:
            self.result.set_provider(self.translator.providers[0].name)
        self.result.show_loading(x, y)
        self.result.src_text = text          # 双语对照 + 朗读英文用
        threading.Thread(target=self._translate_worker,
                         args=(text, cancel, self.translator), daemon=True).start()

    def _translate_worker(self, text, cancel, translator):
        try:
            translator.translate(
                text,
                on_update=lambda acc: task_queue.put(("tip_text", acc)),
                cancel=cancel,
            )
        except TranslationError as e:
            task_queue.put(("tip_error", str(e)))
        except Exception as e:
            log.exception("翻译异常")
            task_queue.put(("tip_error", "翻译失败：%s" % e))

    # ---- 截图翻译 ----
    def _start_ocr(self):
        if self.overlay is not None:
            return
        if not ocr.available():
            self.result.show_at(200, 200, "OCR 组件不可用：缺少 ocr_winrt.ps1")
            return
        self.icon.hide()
        self.overlay = ui.SelectionOverlay(
            self.root,
            on_done=self._on_region_done,
            on_cancel=self._clear_overlay,
        )

    def _clear_overlay(self):
        self.overlay = None

    def _on_region_done(self, bbox):
        self.overlay = None
        threading.Thread(target=self._ocr_worker, args=(bbox,), daemon=True).start()

    def _ocr_worker(self, bbox):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            text = ocr.image_to_text(img)
            if not text:
                task_queue.put(("tip_error", "未识别到文字，换个区域试试"))
                return
            if len(text) > MAX_TEXT:
                text = text[:MAX_TEXT]
            task_queue.put(("ocr_text", (bbox[2], bbox[3], text)))
        except Exception as e:
            log.exception("OCR 失败")
            task_queue.put(("tip_error", "OCR 失败：%s" % e))

    # ---- 设置 ----
    def _open_settings(self):
        if self.settings_win is not None and self.settings_win.win.winfo_exists():
            self.settings_win.win.lift()
            return
        self.settings_win = ui.SettingsDialog(
            self.root, self.cfg, self._apply_settings,
            on_theme=lambda t: self._set_theme(t, keep_settings=True))

    def _apply_settings(self, new_cfg):
        cfgmod.save(new_cfg)
        self.cfg = new_cfg
        try:
            self.translator = Translator(new_cfg, self.cache)
        except TranslationError as e:
            log.warning("翻译源配置无效：%s", e)
            self.translator = Translator({**new_cfg, "provider": "youdao"}, self.cache)
        set_autostart(bool(new_cfg.get("autostart", False)))
        self._unregister_hotkeys()
        self._register_hotkeys()
        ui.set_theme(new_cfg.get("ui", {}).get("theme", ui.DEFAULT_THEME))
        ui.apply_theme(self.root)
        # 字号/高度/主题变化：重建窗口与托盘图标
        try:
            self.icon.win.destroy()
            self.result.win.destroy()
        except Exception:
            pass
        self._build_windows()
        if self.tray is not None:
            try:
                self.tray.icon = self._tray_image()
                self.tray.update_menu()
            except Exception:
                pass
        self.settings_win = None
        log.info("设置已保存")

    # ---- 托盘 ----
    def _tray_image(self):
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((3, 3, 61, 61), fill=ui.rgb(ui.BLUE) + (255,))
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 38)
        except Exception:
            font = ImageFont.load_default()
        d.text((32, 32), "译", font=font, fill=ui.rgb(ui.ON_ACCENT) + (255,), anchor="mm")
        return img

    def _set_theme(self, theme_id, keep_settings=False):
        """切换主题：写配置并即时重建窗口（须主线程执行）

        keep_settings=True 时（设置窗内即选即换）原地重建设置窗，
        让设置窗本身也立刻换上新主题，且位置不动。
        """
        log.info("切换主题：%s", theme_id)
        geo = None
        if keep_settings and self.settings_win is not None:
            try:
                if self.settings_win.win.winfo_exists():
                    geo = self.settings_win.win.geometry()
                    self.settings_win.win.destroy()
            except Exception:
                pass
            self.settings_win = None
        cfg = dict(self.cfg)
        u = dict(cfg.get("ui", {}))
        u["theme"] = theme_id
        cfg["ui"] = u
        self._apply_settings(cfg)
        if geo:
            self._open_settings()
            try:
                self.settings_win.win.geometry(geo)
            except Exception:
                pass

    def _start_tray(self):
        try:
            import pystray

            def toggle_drag(icon, item):
                self.cfg["behavior"]["drag_enabled"] = not self.cfg["behavior"].get("drag_enabled", True)
                cfgmod.save(self.cfg)
                icon.update_menu()

            def theme_item(theme_id):
                # pystray 只接受恰好 (icon, item) 两参的 action，闭包代替默认参数；
                # 统一走任务队列，确保 tkinter 操作在主线程执行
                def pick(icon, item):
                    task_queue.put(("theme", theme_id))

                def is_current(item):
                    return self.cfg.get("ui", {}).get("theme", ui.DEFAULT_THEME) == theme_id

                return pystray.MenuItem(ui.THEMES[theme_id]["label"], pick,
                                        checked=is_current, radio=True)

            theme_menu = pystray.Menu(*[theme_item(t) for t in ui.THEMES])

            menu = pystray.Menu(
                pystray.MenuItem("设置…", lambda: task_queue.put(("settings", None)), default=True),
                pystray.MenuItem("拖选翻译", toggle_drag,
                                 checked=lambda item: self.cfg["behavior"].get("drag_enabled", True)),
                pystray.MenuItem("截图翻译 (Ctrl+Alt+S)", lambda: task_queue.put(("ocr", None))),
                pystray.MenuItem("界面主题", theme_menu),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出 (Ctrl+Alt+Q)", lambda: task_queue.put(("quit", None)),
                                 enabled=not self.selftest),
            )
            self.tray = pystray.Icon("hxy_translate", self._tray_image(), "划词翻译", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
            log.info("托盘已启动")
        except Exception as e:
            log.warning("托盘启动失败：%s", e)

    # ---- 主线程消息泵 ----
    def _poll(self):
        try:
            while True:
                action, payload = task_queue.get_nowait()
                self._handle(action, payload)
        except queue.Empty:
            pass
        try:
            self.root.after(40, self._poll)
        except tk.TclError:
            pass

    def _handle(self, action, payload):
        if action == "theme":
            self._set_theme(payload)
        elif action == "icon":
            x, y, text = payload
            self.pending = (x, y, text)
            self.icon.show(x, y)
        elif action == "translate":
            self._start_translate(*payload)
        elif action == "tip_text":
            self.result.update_text(payload)
        elif action == "tip_error":
            self.result.update_text("翻译失败：" + payload)
        elif action == "tts_state":
            self.result.set_speaking(bool(payload))
        elif action == "ocr_text":
            x, y, text = payload
            if needs_translation(text):
                self._start_translate(x, y, text)
            else:
                self.pending = (x, y, text)
                self.result.show_at(x, y, text)
        elif action == "dismiss":
            if self.pending is not None and not self.result.visible():
                self.icon.hide()
                self.pending = None
        elif action == "esc":
            if self.result.visible():
                self.result.hide()
                self.cancel_event.set()
            elif self.icon.visible():
                self.icon.hide()
                self.pending = None
        elif action == "ocr":
            self._start_ocr()
        elif action == "settings":
            self._open_settings()
        elif action == "quit":
            self.root.quit()


# ---------------- 自检 ----------------
def selftest():
    cfg = cfgmod.load()
    out = {"config": cfgmod.CONFIG_PATH, "log": cfgmod.LOG_PATH,
           "ocr": ocr.available(), "provider": [p.name for p in Translator(cfg).providers]}
    app = App(cfg, selftest=True)
    app.result.show_at(120, 120, "自检文本 self test OK")
    app.icon.show(200, 200)
    app.root.update()
    out["result_visible"] = app.result.visible()
    out["icon_visible"] = app.icon.visible()
    app.result.update_text("多行\n第二行 second line")
    app.root.update()
    # 主题切换链路：任务队列 -> _handle -> _set_theme -> 落盘并生效
    orig_theme = cfg.get("ui", {}).get("theme", ui.DEFAULT_THEME)
    task_queue.put(("theme", "obsidian"))
    app._poll()
    app.root.update()
    cfg2 = cfgmod.load()
    out["theme_switched"] = (cfg2.get("ui", {}).get("theme") == "obsidian"
                             and ui.CURRENT_THEME == "obsidian")
    task_queue.put(("theme", orig_theme))   # 还原，不留副作用
    app._poll()
    app.root.update()
    out["theme_restored"] = cfgmod.load().get("ui", {}).get("theme") == orig_theme
    # 双语对照：译文应同时包含中文译文与英文原文；关闭后只剩译文
    app.result.show_at(120, 120, "")
    app.result.bilingual = True
    app.result.src_text = "hello world"
    app.result.update_text("你好，世界")
    app.root.update()
    full = app.result._full_text()
    out["bilingual_on"] = "你好" in full and "hello world" in full
    app.result.bilingual = False
    app.result.update_text("你好，世界")
    app.root.update()
    out["bilingual_off"] = "hello world" not in app.result._full_text()
    app.result.hide()
    # 朗读英文：中英混排只提取英文片段
    out["speak_english"] = english_only("你好 hello world 世界") == "hello world"
    app.root.destroy()
    line = json.dumps(out, ensure_ascii=False, indent=2)
    try:
        print(line)
    except Exception:
        pass
    try:
        with open(os.path.join(cfgmod.APP_DIR, "selftest.json"), "w", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    return 0


def main():
    parser = argparse.ArgumentParser(description="划词翻译 v2")
    parser.add_argument("--selftest", action="store_true", help="检查窗口与环境后退出")
    args = parser.parse_args()
    setup_logging()
    if args.selftest:
        return selftest()

    cfg = cfgmod.load()
    mutex = single_instance()
    if mutex is None:
        log.info("已有实例在运行，退出")
        return 0
    log.info("翻译源：%s", [p.name for p in Translator(cfg).providers])
    set_autostart(bool(cfg.get("autostart", False)))
    App(cfg).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
