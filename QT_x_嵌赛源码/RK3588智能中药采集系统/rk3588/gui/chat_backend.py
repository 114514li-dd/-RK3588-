#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线药材知识问答（可选扩展 Ollama HTTP）。"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

import yaml

GUI_DIR = Path(__file__).resolve().parent


class HerbChatBackend:
    def __init__(self, knowledge_path: str | Path | None = None):
        path = Path(knowledge_path or GUI_DIR / "herb_knowledge.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.herbs: dict = data.get("herbs", {})
        chat = data.get("chat", {})
        self.welcome = chat.get("welcome", "您好，请问想了解哪种药材？")
        self.fallback = chat.get("fallback", "暂未找到相关内容。")
        self._alias_map = self._build_alias_map()
        self.enabled = True
        self.ollama_url = ""
        self.ollama_model = "qwen2.5:1.5b"

    def _build_alias_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for name, info in self.herbs.items():
            mapping[name] = name
            for alias in info.get("aliases", []):
                mapping[str(alias).lower()] = name
                mapping[str(alias)] = name
        return mapping

    def lookup_herb(self, text: str) -> str | None:
        for key, canonical in self._alias_map.items():
            if key and key in text:
                return canonical
        return None

    def format_detection_entry(self, name: str, confidence: float, bbox: list[int]) -> str:
        info = self.herbs.get(name, {})
        eff = info.get("efficacy", "（暂无功效说明）").strip()
        prop = info.get("properties", "").strip()
        lines = [
            f"对象类别: {name}",
            f"置信度: {confidence:.2f}",
            f"位置: {bbox}",
        ]
        if prop:
            lines.append(f"性状: {prop.splitlines()[0]}")
        lines.append(f"功效: {eff.splitlines()[0] if eff else '—'}")
        return "\n".join(lines)

    def answer(self, question: str, context_herbs: list[str] | None = None) -> str:
        if not self.enabled:
            return "AI 问答已关闭。点击「开启AI模型」后可继续提问。"
        q = question.strip()
        if not q:
            return "请输入问题。"

        herb = self.lookup_herb(q)
        if not herb and context_herbs:
            for h in context_herbs:
                if h in self.herbs:
                    herb = h
                    break

        if herb and herb in self.herbs:
            info = self.herbs[herb]
            if re.search(r"性状|外观|特征|样子|形态", q):
                return f"【{herb}·性状】\n{info.get('properties', self.fallback).strip()}"
            if re.search(r"功效|作用|主治|用途", q):
                return f"【{herb}·功效】\n{info.get('efficacy', self.fallback).strip()}"
            if re.search(r"用法|用量|怎么用|如何服用", q):
                usage = info.get("usage", self.fallback)
                return f"【{herb}·用法用量】\n{usage.strip()}"
            return (
                f"【{herb}】\n"
                f"{info.get('properties', '').strip()}\n\n"
                f"{info.get('efficacy', '').strip()}"
            ).strip()

        if self.ollama_url:
            try:
                return self._ask_ollama(q, context_herbs)
            except Exception:
                pass
        return self.fallback

    def _ask_ollama(self, question: str, context_herbs: list[str] | None) -> str:
        ctx = ""
        if context_herbs:
            for h in context_herbs:
                if h in self.herbs:
                    ctx += self.herbs[h].get("properties", "") + "\n"
        prompt = f"你是中药知识助手。参考：{ctx}\n用户问：{question}"
        payload = (
            '{"model":"%s","prompt":%s,"stream":false}'
            % (self.ollama_model, repr(prompt))
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", self.fallback)
