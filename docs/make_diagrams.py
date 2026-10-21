#!/usr/bin/env python3
"""Схемы пояснительной записки: PNG для Word и исходники draw.io."""

import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(OUT, "img")
DRW = os.path.join(OUT, "diagrams")
os.makedirs(IMG, exist_ok=True)
os.makedirs(DRW, exist_ok=True)

FONT_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)


class Diagram:
    def __init__(self, filename, width, height, title=None):
        self.filename = filename
        self.w = width
        self.h = height
        self.nodes = []
        self.edges = []
        self.lines = []

    def box(self, nid, text, x, y, w, h, kind="process"):
        self.nodes.append({"id": nid, "text": text, "x": x, "y": y, "w": w, "h": h, "kind": kind})
        self.w = max(self.w, x + w + 36)
        self.h = max(self.h, y + h + 36)
        return nid

    def link(self, a, b, label="", start="s", end="n", arrow=True, route=None):
        self.edges.append({
            "a": a, "b": b, "label": label, "start": start, "end": end,
            "arrow": arrow, "route": route,
        })

    def node(self, nid):
        for n in self.nodes:
            if n["id"] == nid:
                return n
        raise KeyError(nid)

    def save(self):
        self._png(os.path.join(IMG, self.filename + ".png"))
        self._drawio(os.path.join(DRW, self.filename + ".drawio"))
        return os.path.join(IMG, self.filename + ".png")

    def _port(self, n, side):
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        return {
            "n": (x + w / 2, y),
            "s": (x + w / 2, y + h),
            "e": (x + w, y + h / 2),
            "w": (x, y + h / 2),
        }[side]

    def _route(self, e):
        if e["route"]:
            return e["route"]
        a = self._port(self.node(e["a"]), e["start"])
        b = self._port(self.node(e["b"]), e["end"])
        if e["start"] == "s" and e["end"] == "n":
            if abs(a[0] - b[0]) < 3:
                return [a, b]
            mid = (a[1] + b[1]) / 2
            return [a, (a[0], mid), (b[0], mid), b]
        if e["start"] == "e" and e["end"] == "w":
            if abs(a[1] - b[1]) < 3:
                return [a, b]
            mid = (a[0] + b[0]) / 2
            return [a, (mid, a[1]), (mid, b[1]), b]
        if e["start"] == "e" and e["end"] == "n":
            return [a, (b[0], a[1]), b]
        if e["start"] == "e" and e["end"] == "s":
            return [a, (b[0], a[1]), b]
        if e["start"] == "w" and e["end"] == "w":
            x = min(a[0], b[0]) - 42
            return [a, (x, a[1]), (x, b[1]), b]
        if e["start"] == "s" and e["end"] == "w":
            return [a, (a[0], b[1]), b]
        if e["start"] == "w" and e["end"] == "n":
            return [a, (b[0], a[1]), b]
        if e["start"] == "n" and e["end"] == "n":
            y = min(a[1], b[1]) - 28
            return [a, (a[0], y), (b[0], y), b]
        return [a, b]

    def _png(self, path):
        im = Image.new("RGB", (int(self.w), int(self.h)), "white")
        dr = ImageDraw.Draw(im)
        for e in self.edges:
            pts = self._route(e)
            dr.line(pts, fill="black", width=2)
            if e["arrow"] and len(pts) >= 2:
                _arrow(dr, pts[-2], pts[-1])
            if e["label"]:
                x = pts[0][0] + 8
                y = pts[0][1] - 22
                if e["start"] == "e":
                    x = pts[0][0] + 6
                    y = pts[0][1] - 26
                dr.text((x, y), e["label"], fill="black", font=font(22, True))
        for n in self.nodes:
            _shape(dr, n)
            _text(dr, n)
        im.save(path, "PNG")

    def _drawio(self, path):
        cells = [
            '<mxCell id="0"/>',
            '<mxCell id="1" parent="0"/>',
        ]
        for i, n in enumerate(self.nodes, start=2):
            style = _dio_style(n["kind"])
            text = (n["text"] or "").replace("&", "&").replace("<", "<").replace(">", ">").replace("\n", "&#10;")
            cells.append(
                f'<mxCell id="{n["id"]}" value="{text}" style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" as="geometry"/>'
                f"</mxCell>"
            )
        eid = 1000
        for e in self.edges:
            pts = self._route(e)
            label = (e["label"] or "").replace("&", "&")
            arr = "block" if e["arrow"] else "none"
            style = (
                "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=%s;"
                "fontFamily=Times New Roman;fontSize=14;labelBackgroundColor=#ffffff;"
            ) % arr
            extra = ""
            if len(pts) > 2:
                bits = []
                for x, y in pts[1:-1]:
                    bits.append(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>')
                extra = '<Array as="points">' + "".join(bits) + "</Array>"
            cells.append(
                f'<mxCell id="e{eid}" value="{label}" style="{style}" edge="1" parent="1" '
                f'source="{e["a"]}" target="{e["b"]}">'
                f'<mxGeometry relative="1" as="geometry">{extra}</mxGeometry></mxCell>'
            )
            eid += 1
        page_w = max(827, int(self.w) + 40)
        page_h = max(1169, int(self.h) + 40)
        xml = (
            '<mxfile host="app.diagrams.net" type="device">\n'
            '  <diagram name="Схема" id="page1">\n'
            f'    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" '
            f'pageHeight="{page_h}" math="0" shadow="0">\n'
            "      <root>\n        "
            + "\n        ".join(cells)
            + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)


def _arrow(dr, p1, p2, size=14):
    import math
    x1, y1 = p1
    x2, y2 = p2
    ang = math.atan2(y2 - y1, x2 - x1)
    left = (x2 - size * math.cos(ang - 0.4), y2 - size * math.sin(ang - 0.4))
    right = (x2 - size * math.cos(ang + 0.4), y2 - size * math.sin(ang + 0.4))
    dr.polygon([(x2, y2), left, right], fill="black")


def _wrap(dr, text, fnt, max_w):
    lines = []
    for part in text.split("\n"):
        words = part.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for word in words[1:]:
            trial = cur + " " + word
            if dr.textlength(trial, font=fnt) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def _text(dr, n):
    kind = n["kind"]
    pad = 18 if kind != "decision" else 36
    max_w = n["w"] - pad * 2
    if kind == "decision":
        max_w = n["w"] * 0.52
    fnt = font(24 if kind != "decision" else 22, bold=(kind in ("term", "header")))
    lines = _wrap(dr, n["text"], fnt, max_w)
    line_h = 28
    total = line_h * len(lines)
    y = n["y"] + (n["h"] - total) / 2
    if kind == "store":
        y += 8
    for line in lines:
        tw = dr.textlength(line, font=fnt)
        x = n["x"] + (n["w"] - tw) / 2
        dr.text((x, y), line, fill="black", font=fnt)
        y += line_h


def _shape(dr, n):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    kind = n["kind"]
    box = [x, y, x + w, y + h]
    if kind in ("process", "header", "card"):
        dr.rectangle(box, fill="white", outline="black", width=2)
    elif kind == "predef":
        dr.rectangle(box, fill="white", outline="black", width=2)
        dr.line([(x + 14, y), (x + 14, y + h)], fill="black", width=2)
        dr.line([(x + w - 14, y), (x + w - 14, y + h)], fill="black", width=2)
    elif kind == "term":
        dr.rounded_rectangle(box, radius=h / 2, fill="white", outline="black", width=2)
    elif kind == "decision":
        cx, cy = x + w / 2, y + h / 2
        dr.polygon([(cx, y), (x + w, cy), (cx, y + h), (x, cy)], fill="white", outline="black")
        dr.line([(cx, y), (x + w, cy), (cx, y + h), (x, cy), (cx, y)], fill="black", width=2)
    elif kind == "data":
        skew = 22
        dr.polygon(
            [(x + skew, y), (x + w, y), (x + w - skew, y + h), (x, y + h)],
            fill="white", outline="black",
        )
        dr.line([(x + skew, y), (x + w, y), (x + w - skew, y + h), (x, y + h), (x + skew, y)], fill="black", width=2)
    elif kind == "input":
        skew = 22
        dr.polygon([(x, y + skew), (x + w, y), (x + w, y + h), (x, y + h)], fill="white", outline="black")
        dr.line([(x, y + skew), (x + w, y), (x + w, y + h), (x, y + h), (x, y + skew)], fill="black", width=2)
    elif kind == "display":
        dr.rounded_rectangle(box, radius=18, fill="white", outline="black", width=2)
        inset = 16
        dr.arc([x - 10, y, x + inset, y + h], 270, 90, fill="black", width=2)
    elif kind == "store":
        ry = 14
        dr.ellipse([x, y, x + w, y + ry * 2], fill="white", outline="black", width=2)
        dr.rectangle([x, y + ry, x + w, y + h - ry], fill="white", outline="white")
        dr.line([(x, y + ry), (x, y + h - ry)], fill="black", width=2)
        dr.line([(x + w, y + ry), (x + w, y + h - ry)], fill="black", width=2)
        dr.arc([x, y + h - ry * 2, x + w, y + h], 0, 180, fill="black", width=2)
        dr.arc([x, y, x + w, y + ry * 2], 180, 360, fill="black", width=2)
    elif kind == "document":
        dr.rectangle([x, y, x + w, y + h - 16], fill="white", outline="black", width=2)
        dr.polygon([(x, y + h - 16), (x, y + h - 4), (x + w / 2, y + h - 18), (x + w, y + h), (x + w, y + h - 16)], fill="white")
        dr.line([(x, y), (x + w, y), (x + w, y + h - 16)], fill="black", width=2)
        dr.line([(x, y), (x, y + h - 8)], fill="black", width=2)
        dr.arc([x, y + h - 28, x + w / 2, y + h], 0, 180, fill="black", width=2)
        dr.arc([x + w / 2, y + h - 28, x + w, y + h], 180, 360, fill="black", width=2)
    else:
        dr.rectangle(box, fill="white", outline="black", width=2)


def _dio_style(kind):
    base = "whiteSpace=wrap;html=1;fontFamily=Times New Roman;fontSize=14;strokeColor=#000000;fillColor=#ffffff;strokeWidth=1.5;"
    return {
        "process": base,
        "header": base + "fontStyle=1;",
        "card": base,
        "predef": base + "shape=process;",
        "term": base + "rounded=1;arcSize=50;",
        "decision": base + "rhombus;",
        "data": base + "shape=parallelogram;perimeter=parallelogramPerimeter;",
        "input": base + "shape=manualInput;",
        "display": base + "shape=display;",
        "store": base + "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=12;",
        "document": base + "shape=document;boundedLbl=1;",
    }.get(kind, base)


def flow_order():
    d = Diagram("Блок-схема_оформление_заказа", 1100, 1500)
    cx = 250
    bw, bh = 460, 78
    d.box("s", "Начало", cx + 130, 24, 200, 52, "term")
    d.box("cat", "Вывод каталога дверей", cx, 110, bw, bh, "display")
    d.box("pick", "Выбор двери", cx, 220, bw, 70, "input")
    d.box("role", "Пользователь\nявляется клиентом?", cx + 50, 330, 360, 150, "decision")
    d.box("login", "Вывод страницы\nвхода", 820, 360, 250, 78, "display")
    d.box("elogin", "Конец", 865, 480, 160, 48, "term")
    d.box("add", "Добавление позиции\nв корзину", cx, 520, bw, 86, "process")
    d.box("more", "Оформить\nзаказ?", cx + 70, 640, 320, 140, "decision")
    d.box("cart", "Вывод корзины", cx, 820, bw, bh, "display")
    d.box("empty", "Корзина\nпуста?", cx + 70, 930, 320, 140, "decision")
    d.box("mempty", "Сообщение\n«Корзина пуста»", 820, 960, 250, 78, "display")
    d.box("eempty", "Конец", 865, 1080, 160, 48, "term")
    d.box("form", "Ввод адреса, телефона\nи комментария", cx, 1110, bw, 86, "input")
    d.box("ok", "Данные\nкорректны?", cx + 70, 1230, 320, 140, "decision")
    d.box("db", "Запись заказа\nи позиций", cx, 1410, bw, 90, "store")
    d.box("clear", "Очистка корзины", cx, 1530, bw, 70, "process")
    d.box("done", "Сообщение\nо номере заказа", cx, 1630, bw, 78, "display")
    d.box("e", "Конец", cx + 130, 1740, 200, 52, "term")
    d.link("s", "cat")
    d.link("cat", "pick")
    d.link("pick", "role")
    d.link("role", "add", "Да")
    d.link("role", "login", "Нет", "e", "w")
    d.link("login", "elogin")
    d.link("add", "more")
    d.link("more", "cart", "Да")
    d.link("more", "cat", "Нет", "w", "w")
    d.link("cart", "empty")
    d.link("empty", "form", "Нет")
    d.link("empty", "mempty", "Да", "e", "w")
    d.link("mempty", "eempty")
    d.link("form", "ok")
    d.link("ok", "db", "Да")
    d.link("ok", "form", "Нет", "w", "w")
    d.link("db", "clear")
    d.link("clear", "done")
    d.link("done", "e")
    return d


def flow_manage_orders():
    d = Diagram("Блок-схема_управление_заказами", 1180, 1400)
    cx = 340
    d.box("s", "Начало", cx + 110, 20, 200, 52, "term")
    d.box("role", "Какая роль\nу пользователя?", cx + 30, 110, 360, 150, "decision")
    d.box("deny", "Отказ в доступе", 900, 140, 240, 70, "display")
    d.box("edeny", "Конец", 940, 250, 160, 48, "term")
    d.box("mgr", "Вывод всех заказов\nклиентов", 40, 320, 300, 86, "display")
    d.box("status", "Ввод нового статуса", 40, 440, 300, 70, "input")
    d.box("save", "Обновление статуса\nв базе", 40, 540, 300, 86, "store")
    d.box("em", "Конец", 110, 660, 160, 48, "term")
    d.box("cli", "Вывод заказов\nэтого клиента", 560, 320, 300, 86, "display")
    d.box("act", "Какое\nдействие?", 590, 440, 240, 140, "decision")
    d.box("can", "Статус позволяет\nизменить заказ?", 860, 640, 280, 150, "decision")
    d.box("edit", "Ввод адреса,\nтелефона, комментария", 520, 680, 300, 86, "input")
    d.box("upd", "Сохранение заказа", 520, 800, 300, 70, "store")
    d.box("dele", "Удаление заказа\nи позиций", 860, 840, 280, 80, "process")
    d.box("no", "Сообщение\nо запрете", 1160, 670, 220, 78, "display")
    d.box("ec", "Конец", 620, 960, 160, 48, "term")
    d.link("s", "role")
    d.link("role", "mgr", "Менеджер", "w", "n")
    d.link("role", "cli", "Клиент", "e", "n")
    d.link("role", "deny", "Иная", "e", "w")
    d.link("deny", "edeny")
    d.link("mgr", "status")
    d.link("status", "save")
    d.link("save", "em")
    d.link("cli", "act")
    d.link("act", "edit", "Изменить", "s", "n")
    d.link("act", "can", "Удалить", "e", "n")
    d.link("can", "dele", "Да")
    d.link("can", "no", "Нет", "e", "w")
    d.link("edit", "upd")
    d.link("upd", "ec")
    d.link("dele", "ec", "", "s", "e")
    return d


def flow_users():
    d = Diagram("Блок-схема_управление_пользователями", 1180, 1280)
    d.box("s", "Начало", 470, 20, 200, 52, "term")
    d.box("act", "Какая\nоперация?", 430, 110, 280, 140, "decision")
    d.box("reg", "Ввод логина, почты,\nпароля и имени", 40, 300, 300, 86, "input")
    d.box("vreg", "Данные уникальны\nи пароль допустим?", 30, 420, 320, 150, "decision")
    d.box("creg", "Создание пользователя\nс ролью «Клиент»", 40, 610, 300, 86, "store")
    d.box("lin", "Открытие сессии", 40, 730, 300, 64, "process")
    d.box("elog", "Ввод логина и пароля", 400, 310, 300, 70, "input")
    d.box("auth", "Учётные данные\nверны?", 410, 420, 280, 140, "decision")
    d.box("sess", "Открытие сессии\nпо роли профиля", 410, 600, 300, 80, "process")
    d.box("bad", "Сообщение об ошибке", 760, 450, 250, 70, "display")
    d.box("man", "Администратор\nподтверждён?", 820, 140, 300, 140, "decision")
    d.box("mform", "Ввод данных\nменеджера", 830, 320, 280, 78, "input")
    d.box("msave", "Создание пользователя\nс ролью «Менеджер»", 810, 430, 320, 86, "store")
    d.box("udel", "Роль — клиент\nили менеджер?", 820, 560, 300, 140, "decision")
    d.box("udel2", "Удаление пользователя", 830, 740, 280, 70, "process")
    d.box("stop", "Отказ: администратора\nудалить нельзя", 1140, 590, 280, 80, "display")
    d.box("e", "Конец", 490, 900, 180, 50, "term")
    d.link("s", "act")
    d.link("act", "reg", "Регистрация", "w", "n")
    d.link("act", "elog", "Вход", "s", "n")
    d.link("act", "man", "Управление", "e", "n")
    d.link("reg", "vreg")
    d.link("vreg", "creg", "Да")
    d.link("vreg", "reg", "Нет", "w", "w")
    d.link("creg", "lin")
    d.link("lin", "e", "", "s", "w")
    d.link("elog", "auth")
    d.link("auth", "sess", "Да")
    d.link("auth", "bad", "Нет", "e", "w")
    d.link("bad", "elog", "", "n", "e")
    d.link("sess", "e")
    d.link("man", "mform", "Да")
    d.link("man", "stop", "Нет", "e", "n")
    d.link("mform", "msave")
    d.link("msave", "udel")
    d.link("udel", "udel2", "Удаление, да")
    d.link("udel", "e", "Только создание", "w", "e")
    d.link("udel2", "e", "", "s", "e")
    return d


def flow_catalog():
    d = Diagram("Блок-схема_управление_каталогом", 1180, 1500)
    d.box("s", "Начало", 470, 20, 200, 52, "term")
    d.box("who", "Пользователь —\nадминистратор?", 420, 110, 320, 150, "decision")
    d.box("view", "Вывод каталога\nпо категориям из БД", 40, 150, 320, 86, "display")
    d.box("eview", "Конец", 120, 280, 160, 48, "term")
    d.box("op", "Какая\nоперация?", 450, 300, 280, 140, "decision")
    d.box("cname", "Ввод названия\nкатегории", 40, 490, 280, 78, "input")
    d.box("cdup", "Такое название\nуже есть?", 30, 600, 300, 140, "decision")
    d.box("cerr", "Сообщение: категория\nуже существует", 360, 620, 280, 86, "display")
    d.box("csave", "Запись категории", 40, 780, 280, 70, "store")
    d.box("cdel", "В категории\nесть двери?", 360, 790, 280, 140, "decision")
    d.box("cdel2", "Удаление категории", 680, 820, 260, 70, "process")
    d.box("cerr2", "Отказ: сначала\nуберите двери", 980, 810, 250, 80, "display")
    d.box("pname", "Ввод карточки двери\nи изображения", 700, 490, 320, 86, "input")
    d.box("psave", "Запись двери\nв выбранную категорию", 710, 610, 300, 86, "store")
    d.box("pdel", "Удаление двери.\nВ заказах остаётся цена", 710, 730, 320, 86, "process")
    d.box("e", "Конец", 490, 1000, 180, 50, "term")
    d.link("s", "who")
    d.link("who", "view", "Нет", "w", "n")
    d.link("view", "eview")
    d.link("who", "op", "Да")
    d.link("op", "cname", "Категория", "w", "n")
    d.link("op", "pname", "Дверь", "e", "n")
    d.link("cname", "cdup")
    d.link("cdup", "csave", "Нет")
    d.link("cdup", "cerr", "Да", "e", "w")
    d.link("cerr", "cname", "", "n", "e")
    d.link("csave", "cdel", "", "s", "n")
    d.link("cdel", "cdel2", "Нет, удалить", "e", "w")
    d.link("cdel", "cerr2", "Да", "e", "w")
    d.link("cdel2", "e", "", "s", "e")
    d.link("pname", "psave")
    d.link("psave", "pdel", "", "s", "n")
    d.link("pdel", "e", "", "s", "e")
    d.link("csave", "e", "Без удаления", "s", "w")
    return d


def flow_news():
    d = Diagram("Блок-схема_управление_новостями", 1100, 1100)
    d.box("s", "Начало", 430, 20, 200, 52, "term")
    d.box("who", "Пользователь —\nадминистратор?", 380, 110, 320, 150, "decision")
    d.box("list", "Вывод новостей\nпо убыванию даты", 40, 140, 300, 86, "display")
    d.box("one", "Вывод выбранной\nновости", 40, 260, 300, 78, "display")
    d.box("elist", "Конец", 110, 370, 160, 48, "term")
    d.box("op", "Какая\nоперация?", 410, 300, 260, 140, "decision")
    d.box("form", "Ввод заголовка,\nтекста и даты", 760, 180, 280, 86, "input")
    d.box("save", "Запись новости", 760, 300, 280, 70, "store")
    d.box("edit", "Выбор новости\nи изменение полей", 760, 410, 280, 86, "input")
    d.box("esave", "Обновление записи", 760, 530, 280, 70, "store")
    d.box("conf", "Подтверждение\nудаления?", 400, 490, 280, 140, "decision")
    d.box("dele", "Удаление новости", 400, 670, 280, 70, "process")
    d.box("e", "Конец", 450, 790, 180, 50, "term")
    d.link("s", "who")
    d.link("who", "list", "Нет", "w", "n")
    d.link("list", "one")
    d.link("one", "elist")
    d.link("who", "op", "Да")
    d.link("op", "form", "Добавить", "e", "s")
    d.link("form", "save")
    d.link("save", "e", "", "s", "e")
    d.link("op", "edit", "Изменить", "e", "n")
    d.link("edit", "esave")
    d.link("esave", "e", "", "s", "e")
    d.link("op", "conf", "Удалить")
    d.link("conf", "dele", "Да")
    d.link("conf", "e", "Нет", "w", "w")
    d.link("dele", "e")
    return d


def sitemap(filename, root, items):
    """items: list of (text, children or None)."""
    d = Diagram(filename, 980, 80 + len(items) * 78 + 40)
    d.box("root", root, 30, 24, 230, 58, "process")
    y = 110
    for i, (text, children) in enumerate(items):
        nid = f"n{i}"
        d.box(nid, text, 340, y, 280, 58, "process")
        d.link("root", nid, arrow=False, start="s", end="w")
        if children:
            cy = y
            for j, child in enumerate(children):
                cid = f"n{i}c{j}"
                d.box(cid, child, 700, cy, 280, 52, "process")
                d.link(nid, cid, arrow=False, start="e", end="w")
                cy += 64
            y = max(y + 74, cy + 8)
        else:
            y += 74
    d.h = max(d.h, y + 20)
    return d


def er():
    d = Diagram("Схема_базы_данных", 1680, 1180)
    specs = [
        ("user", "USER", ["PK id", "username", "password", "email", "first_name", "last_name", "is_superuser", "is_staff", "is_active"], 30, 30),
        ("profile", "PROFILE", ["PK id", "FK user_id", "role", "phone"], 430, 40),
        ("category", "CATEGORY", ["PK id", "name", "UK name_key", "UK slug", "description", "position"], 820, 30),
        ("news", "NEWS", ["PK id", "title", "text", "published_at"], 1240, 40),
        ("cart", "CART", ["PK id", "FK user_id", "created_at"], 30, 430),
        ("citem", "CART_ITEM", ["PK id", "FK cart_id", "FK product_id", "quantity"], 400, 450),
        ("product", "PRODUCT", ["PK id", "FK category_id", "name", "price", "description", "material", "size", "image", "in_stock"], 780, 400),
        ("video", "WORK_VIDEO", ["PK id", "title", "description", "place", "shot_at", "video"], 1240, 360),
        ("order", "ORDER", ["PK id", "FK user_id", "status", "total", "address", "phone", "comment", "created_at"], 30, 780),
        ("oitem", "ORDER_ITEM", ["PK id", "FK order_id", "FK product_id", "product_name", "quantity", "price"], 460, 800),
    ]
    for nid, title, fields, x, y in specs:
        h = 36 + 26 * len(fields)
        d.box(nid, title + "\n" + "\n".join(fields), x, y, 320, h, "header")
    d.link("user", "profile", "1 — 1", "e", "w", arrow=False)
    d.link("user", "cart", "1 — 1", "s", "n", arrow=False)
    d.link("user", "order", "1 — N", "s", "n", arrow=False)
    d.link("cart", "citem", "1 — N", "e", "w", arrow=False)
    d.link("category", "product", "1 — N", "s", "n", arrow=False)
    d.link("product", "citem", "1 — N", "w", "e", arrow=False)
    d.link("product", "oitem", "1 — N", "s", "e", arrow=False)
    d.link("order", "oitem", "1 — N", "e", "w", arrow=False)
    return d


def wire(filename, blocks, w=1040, h=720):
    d = Diagram(filename, w, h)
    for i, (x, y, bw, bh, text, kind) in enumerate(blocks):
        d.box(f"b{i}", text, x, y, bw, bh, kind)
    return d


def header_blocks():
    return [(24, 16, 992, 52, "ПОРТАЛ    Главная | Каталог | Новости | Наши работы | Контакты    Вход / роль", "header")]


def footer_blocks(h=720):
    return [(24, h - 56, 992, 40, "ООО «Портал» · Псков, ул. Металлистов, 12 · телефоны · разработчик", "process")]


def build_wires():
    h = header_blocks()
    f = footer_blocks()
    pages = []
    pages.append(wire("Шаблон_главная", h + [
        (24, 84, 992, 230, "Видеофон шоурума\nЛоготип, название организации, аннотация\nКнопка «Смотреть каталог»", "display"),
        (24, 330, 316, 150, "Категория\nВходные", "card"),
        (364, 330, 316, 150, "Категория\nМежкомнатные", "card"),
        (700, 330, 316, 150, "Категория\nДля частных домов", "card"),
        (24, 496, 316, 150, "Новость 1\nдата и заголовок", "card"),
        (364, 496, 316, 150, "Новость 2", "card"),
        (700, 496, 316, 150, "Новость 3", "card"),
    ] + footer_blocks(720)))
    pages.append(wire("Шаблон_каталог", h + [
        (24, 84, 992, 54, "Заголовок «Каталог» и краткое пояснение иерархии", "process"),
        (24, 152, 120, 40, "Все", "card"),
        (156, 152, 180, 40, "Входные", "card"),
        (348, 152, 220, 40, "Межкомнатные", "card"),
        (580, 152, 260, 40, "Для частных домов", "card"),
        (24, 214, 992, 36, "Название категории и описание", "process"),
        (24, 262, 230, 250, "Фото\nНазвание\nЦена\nВ корзину", "card"),
        (270, 262, 230, 250, "Карточка двери", "card"),
        (516, 262, 230, 250, "Карточка двери", "card"),
        (762, 262, 230, 250, "Карточка двери", "card"),
        (24, 528, 992, 40, "Следующая категория — такой же блок из пяти позиций", "process"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_карточка_двери", h + [
        (24, 84, 992, 32, "Каталог / категория", "process"),
        (24, 128, 500, 470, "Фотография двери", "display"),
        (544, 128, 472, 50, "Категория", "process"),
        (544, 190, 472, 64, "Название двери", "header"),
        (544, 266, 472, 48, "Цена", "process"),
        (544, 326, 472, 110, "Описание", "process"),
        (544, 448, 472, 70, "Материал, размер, наличие", "process"),
        (544, 532, 220, 48, "В корзину", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_новости", h + [
        (24, 84, 992, 56, "Новости — список по убыванию даты", "header"),
        (24, 156, 992, 110, "Дата\nЗаголовок\nТекст новости", "card"),
        (24, 280, 992, 110, "Следующая новость", "card"),
        (24, 404, 992, 110, "Следующая новость", "card"),
        (24, 528, 992, 110, "Следующая новость", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_видео", h + [
        (24, 84, 992, 70, "Наши работы — видео с прошлых заказов", "header"),
        (24, 170, 992, 220, "Видеоплеер", "display"),
        (24, 404, 992, 90, "Название, объект, дата съёмки, описание", "process"),
        (24, 508, 992, 140, "Следующий ролик", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_контакты", h + [
        (24, 84, 992, 56, "Контакты", "header"),
        (24, 160, 480, 280, "Адрес\nТелефоны\nПочта\nЧасы работы", "card"),
        (528, 160, 488, 280, "Разработчик сайта\nЧуров А. А., группа 0434-03\nСтек и дисциплина", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_корзина", h + [
        (24, 84, 992, 50, "Корзина (только клиент)", "header"),
        (24, 150, 992, 90, "Фото | Название | Количество | Сумма | Удалить", "process"),
        (24, 252, 992, 90, "Следующая позиция", "process"),
        (24, 356, 992, 90, "Следующая позиция", "process"),
        (560, 470, 456, 70, "Итого и кнопка «Оформить заказ»", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_мои_заказы", h + [
        (24, 84, 992, 56, "Мои заказы (клиент)", "header"),
        (24, 156, 992, 160, "№ заказа, статус, дата, сумма\nАдрес и телефон\nПозиции\nИзменить | Удалить", "card"),
        (24, 332, 992, 160, "Следующий заказ", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_заказы_менеджера", h + [
        (24, 84, 992, 56, "Заказы клиентов (менеджер)", "header"),
        (24, 156, 992, 180, "№, клиент, статус, адрес, состав\nСписок статусов и кнопка «Сохранить статус»", "card"),
        (24, 352, 992, 180, "Следующий заказ", "card"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_регистрация", h + [
        (24, 84, 992, 56, "Регистрация клиента", "header"),
        (220, 170, 600, 420, "Логин\nИмя и фамилия\nПочта\nТелефон\nПароль и повтор\nКнопка «Создать учётную запись»\nСсылка на вход", "input"),
    ] + footer_blocks()))
    pages.append(wire("Шаблон_панель", h + [
        (24, 84, 992, 48, "Обзор | Категории | Каталог | Новости | Видео | Пользователи", "header"),
        (24, 150, 300, 120, "Категории\nсчётчик", "card"),
        (344, 150, 300, 120, "Двери", "card"),
        (664, 150, 300, 120, "Новости", "card"),
        (24, 290, 992, 300, "Список выбранного раздела\nДобавить / Изменить / Удалить\nФорма с проверкой уникальности категории\nРегистрация менеджера и удаление клиента или менеджера", "process"),
    ] + footer_blocks()))
    return pages


def main():
    diagrams = [
        sitemap("Карта_сайта_гость", "Главная", [
            ("Новости", None),
            ("Контакты", None),
            ("Каталог", ["Входные", "Межкомнатные", "Для частных домов", "Карточка двери"]),
            ("Наши работы", None),
            ("Вход", None),
            ("Регистрация", None),
        ]),
        sitemap("Карта_сайта_клиент", "Главная", [
            ("Каталог", ["Карточка двери"]),
            ("Корзина", ["Изменение количества", "Удаление позиции"]),
            ("Оформление заказа", None),
            ("Мои заказы", ["Просмотр", "Изменение", "Удаление"]),
            ("Новости", None),
            ("Наши работы", None),
            ("Контакты", None),
            ("Выход", None),
        ]),
        sitemap("Карта_сайта_менеджер", "Главная", [
            ("Каталог", None),
            ("Новости", None),
            ("Наши работы", None),
            ("Контакты", None),
            ("Заказы клиентов", ["Просмотр состава", "Смена статуса"]),
            ("Выход", None),
        ]),
        sitemap("Карта_сайта_администратор", "Главная", [
            ("Каталог", None),
            ("Новости", None),
            ("Наши работы", None),
            ("Контакты", None),
            ("Панель", ["Категории", "Двери", "Новости", "Видео работ", "Пользователи"]),
            ("Выход", None),
        ]),
        er(),
        flow_order(),
        flow_manage_orders(),
        flow_users(),
        flow_catalog(),
        flow_news(),
    ]
    diagrams.extend(build_wires())
    for d in diagrams:
        path = d.save()
        print(d.filename, d.w, d.h, os.path.getsize(path))


if __name__ == "__main__":
    main()
