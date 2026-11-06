# -*- coding: utf-8 -*-
"""朗读：调用 Windows 自带语音合成（System.Speech，离线免费）

进程模型：每次朗读起一个后台 powershell，结束/停止时终止它，
不阻塞 Tk 主线程，也不占用常驻进程。
"""
import base64
import logging
import subprocess
import threading

log = logging.getLogger("tts")
CREATE_NO_WINDOW = 0x08000000
MAX_SPEAK = 10000         # 与划词翻译上限对齐；念太长可随时点「停止」


def _script(text, rate=0, volume=100):
    """拼一段 PowerShell：文本用 base64 传，避免引号/中文转义问题"""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.Rate={int(rate)};$s.Volume={int(volume)};"
        f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'));"
        "$s.Speak($t);"
    )


def _encoded_command(script):
    """PowerShell -EncodedCommand 要求 UTF-16LE + base64"""
    raw = script.encode("utf-16-le")
    return base64.b64encode(raw).decode("ascii")


def _no_window_kwargs():
    """隐藏子进程窗口：CREATE_NO_WINDOW + STARTUPINFO(SW_HIDE) 双保险"""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0          # SW_HIDE
    return {"creationflags": CREATE_NO_WINDOW, "startupinfo": si}


class Speaker:
    """单实例朗读器；同一时间只念一段"""

    def __init__(self, on_finish=None, rate=0, volume=100):
        self.on_finish = on_finish
        self.rate = int(rate)
        self.volume = int(volume)
        self._proc = None
        self._lock = threading.Lock()

    def speaking(self):
        p = self._proc
        return bool(p is not None and p.poll() is None)

    def speak(self, text):
        """开始朗读；返回 False 表示没有可念的文本"""
        text = (text or "").strip()
        if not text:
            return False
        text = text[:MAX_SPEAK]
        self.stop()
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
               _encoded_command(_script(text, self.rate, self.volume))]
        try:
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, **_no_window_kwargs())
            threading.Thread(target=self._wait, args=(self._proc,),
                             daemon=True).start()
            return True
        except Exception as e:
            log.warning("朗读启动失败：%s", e)
            return False

    def _wait(self, proc):
        try:
            proc.wait()
        except Exception:
            pass
        if self._proc is proc:
            self._proc = None
            if self.on_finish:
                try:
                    self.on_finish()
                except Exception:
                    pass

    def stop(self):
        with self._lock:
            p, self._proc = self._proc, None
        if p is None:
            return
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    def shutdown(self):
        self.stop()
