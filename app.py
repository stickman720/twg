import json, os, re, random, html, logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup as M, Update
from telegram.error import BadRequest
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, Defaults, filters)

# ===================== تنظیمات (اینجا وارد کنید) =====================
BOT_TOKEN = "8706024591:AAFIknFuh15UyokB64cM51uDJ3H1jkNU3vE"
CHANNEL_1 = "@warbotnews"   # کانال ۱: پیام‌های جهانی و بیانیه‌ها (مثل -1001234567890 یا @name)
CHANNEL_2 = "@warbotwarrroom"   # کانال ۲: پیام‌های لشکرکشی
ADMIN_USERNAME = "alioakII"   # حروف I بزرگ و l کوچک را با دقت چک کنید (یا از ADMIN_ID استفاده کنید)
ADMIN_ID = 0                  # اختیاری و مطمئن‌تر: آیدی عددی تلگرام ادمین (با دستور /id در ربات می‌بینید)
   # پروکسی v2ray (HTTP). برای SOCKS: "socks5h://127.0.0.1:10808" ؛ برای خاموش کردن: ""
# ======================================================================

DB = "/data/data.json"
D = json.load(open(DB, encoding="utf-8")) if os.path.exists(DB) else \
    {"resources": {}, "equipment": {}, "buildings": {}, "users": {}, "requests": [], "attacks": [], "messages": [], "seq": 1}
D["users"] = {k: v for k, v in D["users"].items() if v.get("role") != "admin"}
for k in ("messages", "requests", "attacks"):
    D.setdefault(k, [])
E = html.escape


CATS = ["🚚 ترابری و نیروی انسانی", "🛩 جنگنده‌های نسل 3", "🛩 جنگنده‌های نسل 4", "🛩 جنگنده‌های نسل 4.5",
        "🛩 جنگنده‌های نسل 5 و نسل آینده", "✈️ بمب‌افکن‌ها و هواپیماهای تهاجمی", "🛫 هواپیماهای پشتیبانی و شناسایی",
        "🚁 بالگردهای نظامی", "🛸 پهپادها", "🛡 تانک‌های نسل قدیمی و میانی", "🛡 تانک‌های مدرن", "🚜 تانک سبک و خودروهای رزمی",
        "🚙 نفربرها و خودروهای پیاده‌نظام", "💣 توپخانه و راکت‌اندازها", "🛡 پدافند هوایی", "🚀 موشک‌های راهبردی و سامانه‌های موشکی",
        "⚓ ناوهای هواپیمابر و کشتی‌های بزرگ", "🚢 ناوشکن‌ها و رزم‌ناوها", "🚤 ناوچه‌ها و شناورهای رزمی سبک", "🌊 زیردریایی‌ها",
        "⚓ مین‌روب‌ها و کشتی‌های پشتیبانی", "🔫 سلاح‌های پیاده‌نظام و تجهیزات زمینی", "📡 جنگ الکترونیک، رادار و فرماندهی",
        "🛰 ماهواره‌ها و سامانه‌های فضایی"]


def classify(n):
    g = re.search(r"G([\d.]*)", n)
    g = g.group(1) if g else ""
    if "ترابری" in n or "کامیون" in n or "سرباز" in n: return 0
    if "Anti-Aircraft" in n: return 14
    if "Artillery" in n: return 13
    if "Armoured personal" in n: return 12
    if "Armored car" in n or "Armed_toyota" in n: return 11
    if "🛫" in n: return 16
    if "🚢" in n or "🛳" in n: return 17
    if "🛡" in n: return 9 if g == "3" else 10
    if "✈" in n: return 5
    if "🛩" in n or "Mirage2000" in n: return {"3": 1, "4": 2, "4.5": 3}.get(g, 4)


for _e in D["equipment"].values():
    if "cat" not in _e and classify(_e["name"]) is not None:
        _e["cat"] = classify(_e["name"])


def ecat(i):
    c = D["equipment"].get(i, {}).get("cat")
    return c if isinstance(c, int) and 0 <= c < len(CATS) else 99


def ckey(k):
    return "R" if k[0] == "r" else str(ecat(k[2:]))


def cname(c):
    return "💰 منابع" if c == "R" else (CATS[int(c)] if int(c) < len(CATS) else "📦 سایر")


def save():
    json.dump(D, open(DB + ".t", "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(DB + ".t", DB)


def B(t, d):
    return InlineKeyboardButton(t, callback_data=d)


def nid():
    D["seq"] += 1
    return str(D["seq"])


def kind(i):
    return "r" if i in D["resources"] else "e" if i in D["equipment"] else "b" if i in D["buildings"] else None


def itm(k):
    t, i = k.split(":")
    return (D["resources"] if t == "r" else D["equipment"]).get(i)


def nm(k):
    o = itm(k)
    return o["name"] if o else "؟"


def items(l):
    return "، ".join(f"{x['amt']:,} {E(nm(x['k']))}" for x in l) or "—"


def pairs(d):
    return [{"k": k, "amt": n} for k, n in d.items() if n > 0]


def bal(u, k):
    return u["res" if k[0] == "r" else "eq"].get(k[2:], 0)


def add(u, k, n):
    d = u["res" if k[0] == "r" else "eq"]
    d[k[2:]] = d.get(k[2:], 0) + n


def pay(u, l):
    if not all(bal(u, x["k"]) >= x["amt"] for x in l):
        raise ValueError("منابع یا تجهیزات کافی نیست")
    for x in l:
        add(u, x["k"], -x["amt"])


def lv(b, l):
    d = b["levels"].get(str(l))
    return d and {k: [x for x in d[k] if itm(x["k"])] for k in ("cost", "act", "out")}


def uname(u):
    return E(f"{u.get('flag', '')} {u['name']}".strip()) if u else "؟"


def isadmin(update):
    t = update.effective_user
    ok = bool(ADMIN_ID and t.id == ADMIN_ID) or (t.username or "").lower() == ADMIN_USERNAME.lower().lstrip("@")
    if ok and D.get("admin_id") != t.id:
        D["admin_id"] = t.id
        save()
    return ok


def who_am_i(update):
    t = update.effective_user
    return f"یوزرنیم شما: @{t.username or 'ندارید'}\nآیدی عددی شما: <code>{t.id}</code>"


def me(update):
    t = update.effective_user
    un = (t.username or "").lower()
    for u in D["users"].values():
        if u.get("tg") == t.id:
            return u
    for u in D["users"].values():
        if un and not u.get("tg") and u.get("tgname") == un:
            u["tg"] = t.id
            save()
            return u


def pg(seq, p, n):
    tot = max(1, (len(seq) - 1) // n + 1)
    p = max(0, min(p, tot - 1))
    return seq[p * n:(p + 1) * n], p, tot


def nav(pre, p, tot):
    r = []
    if p > 0:
        r.append(B("⬅️", f"{pre}:{p - 1}"))
    r.append(B(f"{p + 1}/{tot}", "x"))
    if p < tot - 1:
        r.append(B("➡️", f"{pre}:{p + 1}"))
    return r


async def show(update, text, kb=None, photo=None):
    q, m, chat = update.callback_query, (M(kb) if kb else None), update.effective_chat
    try:
        if q and photo and q.message.photo:
            await q.edit_message_caption(caption=text, reply_markup=m)
        elif q and not photo and not q.message.photo:
            await q.edit_message_text(text, reply_markup=m)
        else:
            if q:
                try:
                    await q.message.delete()
                except Exception:
                    pass
            if photo:
                await chat.send_photo(photo, caption=text, reply_markup=m)
            else:
                await chat.send_message(text, reply_markup=m)
    except BadRequest as e:
        if "not modified" in str(e):
            return
        if photo:
            await chat.send_message(text, reply_markup=m)
        else:
            raise


async def home(update, u):
    await show(update, f"🏠 <b>{uname(u)}</b>\nشناسه {u['id']}", MAIN, photo=u.get("pic"))


async def dm(ctx, u, text, kb=None):
    if u and u.get("tg"):
        try:
            await ctx.bot.send_message(u["tg"], text, reply_markup=M(kb) if kb else None)
        except Exception as e:
            logging.warning("dm failed: %s", e)


async def tell_admin(ctx, text):
    aid = ADMIN_ID or D.get("admin_id")
    if not aid:
        logging.warning("admin chat unknown: the admin must send /start to the bot once")
        return
    try:
        await ctx.bot.send_message(aid, text)
    except Exception as e:
        logging.warning("admin message failed: %s", e)


async def post(ctx, chan, text, photo=None, video=None):
    try:
        chan = chan.strip()
        chan = int(chan) if chan.lstrip("-").isdigit() else ("@" + chan.lstrip("@"))
        if photo:
            await ctx.bot.send_photo(chan, photo, caption=text[:1024])
        elif video:
            await ctx.bot.send_video(chan, video, caption=text[:1024])
        else:
            await ctx.bot.send_message(chan, text)
    except Exception as e:
        logging.warning("channel post failed: %s", e)


# ===================== بخش بازیکن =====================
MAIN = [[B("📦 دارایی‌ها", "as:0"), B("🏗 ساختمان‌ها", "bl:0")],
        [B("📬 درخواست‌ها", "rq:0"), B("🔁 تجارت", "tr")],
        [B("⚔️ لشکرکشی", "wr"), B("📜 بیانیه", "dc")],
        [B("🤝 معاهده", "tt"), B("✉️ پیام خصوصی", "pm")]]
WNAME = {"ground": "🪖 زمینی", "air": "✈️ هوایی", "sea": "🚢 دریایی"}
WT = {"ground": "ground", "land": "ground", "زمینی": "ground", "air": "air", "هوایی": "air", "sea": "sea", "naval": "sea", "دریایی": "sea"}
AIR_CATS = {1, 2, 3, 4, 5, 6, 7, 8, 15}   # لشکرکشی هوایی فقط با هواپیما، بالگرد، پهپاد و موشک؛ زمینی و دریایی بدون محدودیت
HOME = [B("🏠 منو", "m")]


def v_assets(u, p):
    eq = sorted([(i, n) for i, n in u["eq"].items() if n > 0 and i in D["equipment"]], key=lambda x: (ecat(x[0]), int(x[0])))
    part, p, tot = pg(eq, p, 25)
    t = (f"🏳️ <b>{uname(u)}</b> — شناسه {u['id']}\n\n💰 <b>منابع</b>\n" +
         "\n".join(f"{E(r['name'])}: {u['res'].get(i, 0):,}" for i, r in D["resources"].items()) + "\n\n⚔️ <b>تجهیزات</b>")
    last = None
    for i, n in part:
        if ecat(i) != last:
            last = ecat(i)
            t += f"\n\n<b>{cname(str(last))}</b>"
        t += f"\n{E(D['equipment'][i]['name'])}: {n:,}"
    if not part:
        t += "\n—"
    return t, [nav("as", p, tot), HOME]


def bcat(b):
    c = b.get("cat", "99")
    return -1 if c == "R" else int(c)


def v_blist(u, p):
    L = sorted([D["buildings"][i] for i in u.get("unl", {}) if i in D["buildings"]], key=lambda b: (bcat(b), int(b["id"])))
    part, p, tot = pg(L, p, 8)

    def st(b):
        l = u["bld"].get(b["id"], 0)
        if l:
            return f"لول {l}" + (" ⏸ غیرفعال" if b["id"] in u.get("off", {}) else "")
        return "ساخته نشده" if b["id"] in u.get("lic", {}) else "🔬 نیاز به تکنولوژی"
    kb = [[B(f"{b['name']} — {st(b)}", f"bd:{b['id']}")] for b in part]
    t = "🏗 <b>ساختمان‌ها</b>" + ("" if L else "\n\nهنوز هیچ ساختمانی برای شما باز نشده؛ با ادمین هماهنگ کنید.")
    return t, kb + [nav("bl", p, tot), HOME]


def v_bdet(u, bid):
    b = D["buildings"][bid]
    l = u["bld"].get(bid, 0)
    back = [[B("⬅️ ساختمان‌ها", "bl:0")]]
    if bid not in u.get("unl", {}):
        return f"🔒 <b>{E(b['name'])}</b> برای شما قفل است.", back
    if bid not in u.get("lic", {}):
        d1 = lv(b, 1)
        return (f"🔬 <b>{E(b['name'])}</b>\n\nبرای باز کردن این ساختمان تکنولوژی لازم است:\n{items(b.get('unlock', []))}"
                f"\n\nهزینه ساخت لول ۱: {items(d1['cost'])}\nمصرف هر فعالیت: {items(d1['act'])}\nتولید: {items(d1['out'])}",
                [[B("🔬 باز کردن با تکنولوژی", f"bt:{bid}")]] + back)
    cur, nx = (lv(b, l) if l else None), lv(b, l + 1)
    off = bid in u.get("off", {})
    t = f"🏗 <b>{E(b['name'])}</b> — {'لول ' + str(l) if l else 'ساخته نشده'}" + ("\n⏸ <b>غیرفعال</b> (در فعالیت همگانی منابعی مصرف و تولید نمی‌شود)" if off and l else "")
    if cur:
        t += f"\n\nفعلی: مصرف {items(cur['act'])} ← تولید {items(cur['out'])}"
    kb = []
    if nx:
        t += f"\n\n{'⬆️ آپگرید به لول ' + str(l + 1) if l else '🔨 ساخت'}\nهزینه: {items(nx['cost'])}\nلول بعد: مصرف {items(nx['act'])} ← تولید {items(nx['out'])}"
        kb = [[B("⬆️ آپگرید" if l else "🔨 ساخت", f"bb:{bid}")]]
    else:
        t += "\n\n✅ حداکثر لول"
    if l:
        kb.append([B("▶️ فعال کردن" if off else "⏸ غیرفعال کردن", f"bo:{bid}")])
    return t, kb + back


def rline(r):
    f, t = D["users"].get(r["from"]), D["users"].get(r["to"])
    if r["type"] == "trade":
        return f"🔁 {uname(f)} می‌دهد: {items(r['give'])}\nو از {uname(t)} می‌گیرد: {items(r['get'])}"
    return f"🤝 معاهده {uname(f)} ← {uname(t)}:\n{E(r['text'])}"


def rkb(r):
    return [[B("✅ تایید", f"ra:{r['id']}:1"), B("❌ رد", f"ra:{r['id']}:0")]]


def v_reqs(u, p):
    alerts = [a for a in D["attacks"] if a["to"] == u["id"] and a["status"] == "active"]
    t = "".join(f"🔴🔴 <b>هشدار حمله!</b> {uname(D['users'].get(a['from']))} لشکرکشی {WNAME.get(a.get('wtype'), '')} به شهر {E(a.get('city', '؟'))} آغاز کرده ({a['hours']:g} ساعت)\n" for a in alerts)
    pend = [r for r in D["requests"] if r["to"] == u["id"] and r["status"] == "pending"]
    part, p, tot = pg(pend, p, 4)
    t += "\n📬 <b>درخواست‌ها</b>\n" + ("\n\n".join(f"#{r['id']}\n{rline(r)}" for r in part) or "درخواستی نیست.")
    kb = [[B(f"✅ #{r['id']}", f"ra:{r['id']}:1"), B(f"❌ #{r['id']}", f"ra:{r['id']}:0")] for r in part]
    return t, kb + [nav("rq", p, tot), HOME]


def v_users(u, p):
    part, p, tot = pg([x for x in D["users"].values() if x["id"] != u["id"]], p, 8)
    return "کشور مقابل را انتخاب کنید:", [[B(uname(x), f"us:{x['id']}")] for x in part] + [nav("pu", p, tot), HOME]


STG = {"give": "📤 چه چیزی می‌دهید؟", "get": "📥 چه چیزی می‌گیرید؟", "units": "⚔️ چه تجهیزاتی می‌فرستید؟"}


def v_pick(u, st, p, cat=None):
    s = st["stage"]
    pool = [("e:" + i, r) for i, r in D["equipment"].items()]
    if s != "units":
        pool = [("r:" + i, r) for i, r in D["resources"].items()] + pool
    if s != "get":
        pool = [(k, r) for k, r in pool if bal(u, k) > 0]
    if s == "units" and st.get("wtype") == "air":
        pool = [(k, r) for k, r in pool if ecat(k[2:]) in AIR_CATS]
    t = f"{STG[s]}\nانتخاب‌شده: {items(pairs(st[s]))}"
    tail = [[B("✅ ادامه", "nx"), B("❌ لغو", "m")]]
    if cat is None:
        cs = sorted({ckey(k) for k, _ in pool}, key=lambda c: (c != "R", int(c) if c != "R" else 0))
        part, p, tot = pg(cs, p, 8)
        kb = [[B(f"{cname(c)} ({sum(1 for k, _ in pool if ckey(k) == c)})", f"pc:{c}:0")] for c in part]
        return t + "\nدسته را انتخاب کنید:", kb + [nav("pi", p, tot)] + tail
    part, p, tot = pg([(k, r) for k, r in pool if ckey(k) == cat], p, 8)
    kb = [[B(r["name"] + (f" ({bal(u, k):,})" if s != "get" else ""), "it:" + k)] for k, r in part]
    return t + f"\n<b>{cname(cat)}</b>", kb + [nav(f"pc:{cat}", p, tot), [B("⬅️ دسته‌ها", "pi:0")]] + tail


def confirm_text(u, st):
    to = uname(D["users"][st["to"]])
    if st["k"] == "trade":
        return f"تایید نهایی تجارت با {to}\nمی‌دهم: {items(pairs(st['give']))}\nمی‌گیرم: {items(pairs(st['get']))}"
    return (f"تایید نهایی لشکرکشی {WNAME[st['wtype']]} به {to}\nشهر: {E(st['city'])}\nتجهیزات: {items(pairs(st['units']))}"
            f"\nمدت: {st['hours']:g} ساعت\n(از دارایی شما کسر می‌شود؛ تعداد نیروها فقط به ادمین اعلام می‌شود)")


async def p_cb(update, ctx, u, a):
    c, st = a[0], ctx.user_data.get("st") or {}
    if c == "m":
        ctx.user_data.clear()
        return await home(update, u)
    if c == "as":
        return await show(update, *v_assets(u, int(a[1])))
    if c == "bl":
        return await show(update, *v_blist(u, int(a[1])))
    if c == "bd":
        return await show(update, *v_bdet(u, a[1]))
    if c == "bo":
        if u["bld"].get(a[1], 0) < 1:
            raise ValueError("این ساختمان هنوز ساخته نشده")
        off = u.setdefault("off", {})
        if a[1] in off:
            off.pop(a[1])
        else:
            off[a[1]] = 1
        save()
        return await show(update, *v_bdet(u, a[1]))
    if c == "bt":
        b = D["buildings"][a[1]]
        if a[1] not in u.get("unl", {}):
            raise ValueError("این ساختمان برای شما قفل است")
        pay(u, [x for x in b.get("unlock", []) if itm(x["k"])])
        u.setdefault("lic", {})[a[1]] = 1
        save()
        return await show(update, *v_bdet(u, a[1]))
    if c == "bb":
        if a[1] not in u.get("unl", {}) or a[1] not in u.get("lic", {}):
            raise ValueError("ابتدا ساختمان باید باز شود و با تکنولوژی فعال شود")
        b = D["buildings"][a[1]]
        d = lv(b, u["bld"].get(a[1], 0) + 1)
        if not d:
            raise ValueError("حداکثر لول")
        pay(u, d["cost"])
        u["bld"][a[1]] = u["bld"].get(a[1], 0) + 1
        save()
        return await show(update, *v_bdet(u, a[1]))
    if c == "rq":
        return await show(update, *v_reqs(u, int(a[1])))
    if c == "ra":
        return await answer(update, ctx, u, a[1], a[2] == "1")
    if c == "wr":
        return await show(update, "⚔️ <b>لشکرکشی</b>\nنوع لشکرکشی را انتخاب کنید:", [[B(n, f"wt:{k}")] for k, n in WNAME.items()] + [HOME])
    if c == "wt":
        if a[1] not in WNAME:
            raise ValueError("نوع نامعتبر")
        ctx.user_data["st"] = {"k": "war", "wtype": a[1], "stage": "to", "give": {}, "get": {}, "units": {}}
        return await show(update, *v_users(u, 0))
    if c in ("tr", "tt", "pm"):
        ctx.user_data["st"] = {"k": {"tr": "trade", "tt": "treaty", "pm": "pm"}[c], "stage": "to", "give": {}, "get": {}, "units": {}}
        return await show(update, *v_users(u, 0))
    if c == "pr":
        if a[1] not in D["users"]:
            raise ValueError("کشور پیدا نشد")
        ctx.user_data["st"] = {"k": "pm", "to": a[1], "await": "text"}
        return await show(update, f"متن پاسخ برای {uname(D['users'][a[1]])} را بنویسید:", [HOME])
    if c == "pu":
        return await show(update, *v_users(u, int(a[1])))
    if c == "dc":
        ctx.user_data["st"] = {"k": "decl", "await": "text"}
        return await show(update, "متن بیانیه را بنویسید (یا یک عکس/ویدیو همراه با توضیح بفرستید):", [HOME])
    if not st:
        return await home(update, u)
    if c == "us":
        st["to"] = a[1]
        if st["k"] in ("treaty", "pm"):
            st["await"] = "text"
            return await show(update, "متن معاهده را بنویسید:" if st["k"] == "treaty" else "متن پیام خصوصی را بنویسید:", [HOME])
        if st["k"] == "war":
            st["await"] = "city"
            return await show(update, f"نام شهر هدف را تایپ کنید ({WNAME[st['wtype']]}):", [HOME])
        st["stage"] = "give"
        return await show(update, *v_pick(u, st, 0))
    if c == "pc":
        return await show(update, *v_pick(u, st, int(a[2]), a[1]))
    if c == "pi":
        return await show(update, *v_pick(u, st, int(a[1])))
    if c == "it":
        st["cur"], st["await"] = a[1] + ":" + a[2], "amt"
        mx = f" (حداکثر {bal(u, st['cur']):,})" if st["stage"] != "get" else ""
        return await show(update, f"تعداد «{E(nm(st['cur']))}» را بنویسید{mx}:", [HOME])
    if c == "nx":
        if st["k"] == "trade" and st["stage"] == "give":
            st["stage"] = "get"
            return await show(update, *v_pick(u, st, 0))
        if st["k"] == "trade":
            if not st["give"] and not st["get"]:
                raise ValueError("حداقل یک آیتم انتخاب کنید")
            return await show(update, confirm_text(u, st), [[B("✅ ارسال", "sd")], HOME])
        if not st["units"]:
            raise ValueError("حداقل یک تجهیز انتخاب کنید")
        st["await"] = "hours"
        return await show(update, "⏱ مدت لشکرکشی را به ساعت بنویسید:", [HOME])
    if c == "sd":
        return await send(update, ctx, u, st)


async def send(update, ctx, u, st):
    to = D["users"][st["to"]]
    if st["k"] == "trade":
        give = pairs(st["give"])
        if not all(bal(u, x["k"]) >= x["amt"] for x in give):
            raise ValueError("موجودی کافی نیست")
        r = {"id": nid(), "type": "trade", "from": u["id"], "to": to["id"], "status": "pending", "give": give, "get": pairs(st["get"]), "text": ""}
        D["requests"].append(r)
        save()
        await dm(ctx, to, f"📬 <b>درخواست جدید</b>\n{rline(r)}", rkb(r))
        msg = "✅ درخواست ارسال شد."
    else:
        units = pairs(st["units"])
        pay(u, units)
        a = {"id": nid(), "from": u["id"], "to": to["id"], "hours": st["hours"], "units": units, "status": "active",
             "wtype": st["wtype"], "city": st["city"]}
        D["attacks"].append(a)
        save()
        await dm(ctx, to, f"🔴🔴 <b>هشدار حمله!</b>\n{uname(u)} لشکرکشی {WNAME[a['wtype']]} به شهر {E(a['city'])} آغاز کرد ({a['hours']:g} ساعت)")
        await post(ctx, CHANNEL_2, f"⚔️ <b>لشکرکشی #{a['id']}</b>\n{uname(u)} ← {uname(to)}\nنوع: {WNAME[a['wtype']]}\nشهر: {E(a['city'])}\nمدت: {a['hours']:g} ساعت",
                   photo=D.get("warpics", {}).get(a["wtype"]))
        await tell_admin(ctx, f"🗡 <b>لشکرکشی #{a['id']}</b>\n{uname(u)} ← {uname(to)}\nنوع: {WNAME[a['wtype']]}\nشهر: {E(a['city'])}\nنیرو: {items(units)}\nمدت: {a['hours']:g} ساعت")
        msg = "✅ لشکرکشی آغاز شد."
    ctx.user_data.clear()
    await show(update, msg, [HOME])


async def answer(update, ctx, u, rid, yes):
    r = next((x for x in D["requests"] if x["id"] == rid), None)
    if not r or r["to"] != u["id"] or r["status"] != "pending":
        raise ValueError("درخواست معتبر نیست")
    a = D["users"].get(r["from"])
    if yes and r["type"] == "trade":
        if not a or not all(bal(a, x["k"]) >= x["amt"] for x in r["give"]) or not all(bal(u, x["k"]) >= x["amt"] for x in r["get"]):
            raise ValueError("موجودی یکی از طرفین کافی نیست")
        for x in r["give"]:
            add(a, x["k"], -x["amt"]); add(u, x["k"], x["amt"])
        for x in r["get"]:
            add(u, x["k"], -x["amt"]); add(a, x["k"], x["amt"])
    r["status"] = "accepted" if yes else "rejected"
    save()
    await dm(ctx, a, f"{'✅ تایید شد' if yes else '❌ رد شد'}:\n{rline(r)}")
    if update.callback_query.message.text and update.callback_query.message.text.startswith("📬 درخواست جدید"):
        return await show(update, f"{'✅ تایید شد' if yes else '❌ رد شد'}\n{rline(r)}", [HOME])
    await show(update, *v_reqs(u, 0))


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u, st = me(update), ctx.user_data.get("st")
    if not u or not st or not st.get("await"):
        return
    w, txt = st["await"], update.message.text.strip()
    try:
        if w == "city":
            st["city"], st["await"], st["stage"] = txt[:60], None, "units"
            return await show(update, *v_pick(u, st, 0))
        if w in ("amt", "hours"):
            n = float(txt.replace(",", ""))
            if n <= 0:
                raise ValueError("عدد باید مثبت باشد")
            if w == "hours":
                st["hours"], st["await"] = n, None
                return await show(update, confirm_text(u, st), [[B("✅ آغاز لشکرکشی", "sd")], HOME])
            n, k, s = int(n), st["cur"], st["stage"]
            if s != "get" and st[s].get(k, 0) + n > bal(u, k):
                raise ValueError("بیشتر از موجودی شماست")
            st[s][k] = st[s].get(k, 0) + n
            st["await"] = None
            return await show(update, f"{STG[s]}\nانتخاب‌شده: {items(pairs(st[s]))}", [[B("➕ آیتم دیگر", "pi:0")], [B("✅ ادامه", "nx"), B("❌ لغو", "m")]])
        text = txt[:2000]
        if st["k"] == "pm":
            to = D["users"].get(st["to"])
            if not to or not to.get("tg"):
                raise ValueError("این کشور هنوز ربات را شروع نکرده و پیام نمی‌گیرد")
            try:
                await ctx.bot.send_message(to["tg"], f"✉️ <b>پیام خصوصی از {uname(u)}</b>\n\n{E(text)}", reply_markup=M([[B("↩️ پاسخ", f"pr:{u['id']}")]]))
            except Exception:
                raise ValueError("پیام ارسال نشد؛ احتمالاً بازیکن ربات را مسدود کرده است")
            ctx.user_data.clear()
            return await show(update, f"✅ پیام برای {uname(to)} ارسال شد.", [HOME])
        if st["k"] in ("decl", "chat"):
            head = f"{uname(u)}" + (" — 📜 <b>بیانیه</b>" if st["k"] == "decl" else "")
            await post(ctx, CHANNEL_1, f"{head}\n\n{E(text)}")
            D["messages"].append({"uid": u["id"], "kind": st["k"], "text": text})
            msg = "✅ منتشر شد."
        else:
            r = {"id": nid(), "type": "treaty", "from": u["id"], "to": st["to"], "status": "pending", "give": [], "get": [], "text": text}
            D["requests"].append(r)
            await dm(ctx, D["users"][st["to"]], f"📬 <b>درخواست جدید</b>\n{rline(r)}", rkb(r))
            msg = "✅ درخواست معاهده ارسال شد."
        save()
        ctx.user_data.clear()
        await show(update, msg, [HOME])
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")


# ===================== بخش ادمین =====================
AMENU = [[B("👥 کاربران", "A:us:0"), B("💰 منابع", "A:rs:0")], [B("🏭 ساختمان‌ها", "A:bd:0"), B("⬆️ آپگرید", "A:up:0")],
         [B("⚔️ تجهیزات", "A:eq:0"), B("🔁 تجارت", "A:tr:0")], [B("🗡 لشکرکشی", "A:wr:0"), B("📜 بیانیه/معاهده", "A:dc:0")],
         [B("⚡ فعال‌سازی ساختمان‌ها (همه بازیکنان)", "A:all")]]
AHOME = [B("🏠 پنل", "A:m")]
ST = {"pending": "⏳", "accepted": "✅", "rejected": "❌", "active": "🔴 در جریان", "closed": "⚪ پایان"}
HELP = {"wr": "/warphoto ground|air|sea (یا زمینی/هوایی/دریایی) — بعد عکس را بفرستید؛ /warphoto air off = حذف\nعکس همان نوع به پست لشکرکشی در کانال ۲ اضافه می‌شود. تعداد نیروها فقط برای ادمین می‌آید.", "us": "/activate [شناسه‌کاربر]  (فعال‌سازی ساختمان‌ها؛ بدون شناسه = همه بازیکنان)\n/unlock شناسه‌کاربر کد [کد ...] (یا all)\n/lock شناسه‌کاربر کد (یا all)\n/photo شناسه (بعد عکس را بفرستید؛ /photo شناسه off = حذف)\n/addplayer @username نام کشور\n/name شناسه نام‌جدید\n/flag شناسه 🇮🇷\n/delplayer شناسه\n/set شناسه‌کاربر شناسه‌آیتم مقدار\n/add شناسه‌کاربر شناسه‌آیتم ±مقدار",
        "rs": "/addres نام | مقدار اولیه\n/edit شناسه نام | مقدار اولیه\n/del شناسه", "eq": "/addeq نام | مقدار اولیه | شماره دسته\n/cat شناسه شماره‌دسته  (لیست دسته‌ها: /cats)\n/edit شناسه نام | مقدار اولیه\n/del شناسه",
        "bd": "/unlock شناسه‌کاربر کد [کد ...] (یا all)  ·  /lock شناسه‌کاربر کد\n/tech کد مقدار  ·  /binfo کد\n/addb نام\n/edit شناسه نام\n/del شناسه\n/lvl شناسه 1  (و در خطوط بعد: cost: 3 100, 5 20 / act: ... / out: ...)",
        "up": "/lvl شناسه‌ساختمان لول  (لول ۲ به بعد؛ خطوط cost: / act: / out:)\n/dellvl شناسه لول"}


def a_bview(c, cat, p):
    L = sorted([b for b in D["buildings"].values() if b.get("cat", "99") == cat], key=lambda b: int(b["id"]))
    part, p, tot = pg(L, p, 4 if c == "bc" else 2)
    t = f"{'🏭' if c == 'bc' else '⬆️'} <b>{cname(cat)}</b>\n"
    for b in part:
        t += f"\n<code>{b['id']}</code> <b>{E(b['name'])}</b>"
        if c == "bc":
            t += f"\n  🔬 تکنولوژی لازم: {items(b.get('unlock', []))}"
        for l, d in sorted(b["levels"].items(), key=lambda x: int(x[0])):
            if (c == "bc") == (l == "1"):
                t += f"\n  لول {l}: هزینه {items(d['cost'])} | مصرف {items(d['act'])} | تولید {items(d['out'])}"
    back = "bd" if c == "bc" else "up"
    return t + "\n\n" + HELP[back], [nav(f"A:{c}:{cat}", p, tot), [B("⬅️ دسته‌ها", f"A:{back}:0")], AHOME]


def a_view(tab, p):
    kb, t = [], ""
    if tab == "us":
        part, p, tot = pg(list(D["users"].values()), p, 8)
        t = "👥 <b>کاربران</b>"
        kb = [[B(f"{uname(x)} · {x['id']}", f"A:u:{x['id']}")] for x in part]
    elif tab in ("rs", "eq"):
        L = list(D["resources"].values()) if tab == "rs" else sorted(D["equipment"].values(), key=lambda x: (ecat(x["id"]), int(x["id"])))
        part, p, tot = pg(L, p, 25)
        t = "💰 <b>منابع</b>" if tab == "rs" else "⚔️ <b>تجهیزات</b>"
        last = None
        for x in part:
            if tab == "eq" and ecat(x["id"]) != last:
                last = ecat(x["id"])
                t += f"\n\n<b>{cname(str(last))}</b>"
            t += f"\n<code>{x['id']}</code> {E(x['name'])} — {x['initial']:,}"
    elif tab in ("bd", "up"):
        allb = list(D["buildings"].values())
        cs = sorted({b.get("cat", "99") for b in allb}, key=lambda c: -1 if c == "R" else int(c))
        part, p, tot = pg(cs, p, 10)
        t = ("🏭 <b>ساختمان‌ها</b>" if tab == "bd" else "⬆️ <b>آپگرید</b>") + f"\nمجموع: {len(allb)} ساختمان\nدسته را انتخاب کنید:"
        pre = "bc" if tab == "bd" else "uc"
        kb = [[B(f"{cname(c)} ({sum(1 for b in allb if b.get('cat', '99') == c)})", f"A:{pre}:{c}:0")] for c in part]
    elif tab == "tr":
        part, p, tot = pg([r for r in D["requests"] if r["type"] == "trade"][::-1], p, 6)
        t = "🔁 <b>تجارت</b>\n\n" + "\n\n".join(f"{rline(r)}\n{ST[r['status']]}" for r in part)
    elif tab == "wr":
        part, p, tot = pg(D["attacks"][::-1], p, 4)
        t = "🗡 <b>لشکرکشی</b> (نیروهای سالم را با /add به دارایی برگردانید)\n\n" + "\n\n".join(
            f"#{a['id']} {uname(D['users'].get(a['from']))} ← {uname(D['users'].get(a['to']))}\n{WNAME.get(a.get('wtype'), '')} · شهر {E(a.get('city', '؟'))}\n{items(a['units'])} · {a['hours']:g} ساعت · {ST[a['status']]}" for a in part)
        kb = [[B(f"پایان لشکرکشی #{a['id']}", f"A:close:{a['id']}")] for a in part if a["status"] == "active"]
    else:
        ev = [("📜 " + uname(D["users"].get(m["uid"])) + ": " + E(m["text"])) for m in D["messages"] if m["kind"] == "decl"] + \
             [f"{rline(r)}\n{ST[r['status']]}" for r in D["requests"] if r["type"] == "treaty"]
        part, p, tot = pg(ev[::-1], p, 5)
        t = "📜 <b>بیانیه‌ها و معاهدات</b>\n\n" + "\n\n".join(part)
    t += "\n\n" + HELP.get(tab, "")
    return t, kb + [nav(f"A:{tab}", p, tot), AHOME]


async def run_activation(ctx, only=None):
    rep = []
    for u in D["users"].values():
        if only and u["id"] != only:
            continue
        ok = sk = pz = 0
        for bid, l in u["bld"].items():
            if bid in u.get("off", {}):
                pz += 1
                continue
            b = D["buildings"].get(bid)
            d = b and lv(b, l)
            if not d:
                continue
            try:
                pay(u, d["act"])
                for x in d["out"]:
                    add(u, x["k"], x["amt"])
                ok += 1
            except ValueError:
                sk += 1
        rep.append(f"{uname(u)}: ✅ {ok} · ⏭ {sk} (کمبود منابع)" + (f" · ⏸ {pz} (غیرفعال)" if pz else ""))
        if ok:
            await dm(ctx, u, "⚡ ساختمان‌های شما فعال شدند.")
    save()
    return ("⚡ <b>گزارش فعال‌سازی</b>\n" + "\n".join(rep or ["بازیکنی پیدا نشد."]))[:3900]


async def a_cb(update, ctx, a):
    c = a[0]
    if c == "m":
        return await show(update, "🛠 <b>پنل ادمین</b>", AMENU)
    if c == "u":
        u = D["users"][a[1]]
        t = (f"👤 <b>{uname(u)}</b> · شناسه {u['id']} · @{u.get('tgname') or '?'}\n\n" +
             "\n".join(f"{E(D['resources'][i]['name'])}: {n:,}" for i, n in u["res"].items() if i in D["resources"]) + "\n\n" +
             "\n".join(f"{E(D['equipment'][i]['name'])}: {n:,}" for i, n in u["eq"].items() if n and i in D["equipment"]) + "\n\n" +
             "\n".join(f"{E(D['buildings'][i]['name'])}: لول {n}" for i, n in u["bld"].items() if i in D["buildings"]))
        return await show(update, t[:3900], [[B("⬅️", "A:us:0")]])
    if c == "close":
        for x in D["attacks"]:
            if x["id"] == a[1] and x["status"] == "active":
                x["status"] = "closed"
                save()
                await post(ctx, CHANNEL_2, f"⚪ لشکرکشی #{x['id']} پایان یافت.")
        return await show(update, *a_view("wr", 0))
    if c in ("bc", "uc"):
        return await show(update, *a_bview(c, a[1], int(a[2])))
    if c == "all":
        return await show(update, "⚡ همه ساختمان‌های همه بازیکنان یک بار فعال شود؟", [[B("✅ بله", "A:ally"), B("❌ خیر", "A:m")]])
    if c == "ally":
        return await show(update, await run_activation(ctx), [AHOME])

    return await show(update, *a_view(c, int(a[1])))


def adm(f):
    async def w(update, ctx):
        if not isadmin(update):
            return await update.message.reply_text("⛔ شما ادمین نیستید.\n" + who_am_i(update))
        try:
            await f(update, ctx, update.message.text.partition(" ")[2].strip(), ctx.args)
            save()
        except Exception as e:
            logging.info("admin cmd error: %s", e)
            await update.message.reply_text("❌ فرمت یا شناسه نادرست است. /help را ببینید.")
    return w


def split_ni(s):
    n, _, v = s.partition("|")
    return n.strip(), int(v.strip() or 0)


@adm
async def c_addplayer(update, ctx, s, a):
    who, name = a[0], " ".join(a[1:])
    uid = str(random.randint(1000, 9999))
    while uid in D["users"]:
        uid = str(random.randint(1000, 9999))
    u = {"id": uid, "role": "user", "name": name, "flag": "", "photo": "", "tg": None, "tgname": None,
         "res": {k: v["initial"] for k, v in D["resources"].items()}, "eq": {k: v["initial"] for k, v in D["equipment"].items()}, "bld": {}}
    if who.lstrip("-").isdigit():
        u["tg"] = int(who)
    else:
        u["tgname"] = who.lstrip("@").lower()
    D["users"][uid] = u
    await update.message.reply_text(f"✅ ساخته شد. شناسه: {uid}\nبازیکن باید /start را در ربات بزند.")


@adm
async def c_delplayer(update, ctx, s, a):
    D["users"].pop(a[0])
    await update.message.reply_text("✅ حذف شد.")


@adm
async def c_name(update, ctx, s, a):
    D["users"][a[0]]["name"] = " ".join(a[1:])
    await update.message.reply_text("✅")


@adm
async def c_flag(update, ctx, s, a):
    D["users"][a[0]]["flag"] = a[1]
    await update.message.reply_text("✅")


async def setadd(update, a, rel):
    u, i, n = D["users"][a[0]], a[1], int(a[2])
    k = kind(i)
    d = {"r": u["res"], "e": u["eq"], "b": u["bld"]}[k]
    d[i] = max(0, (d.get(i, 0) if rel else 0) + n)
    if k == "b" and d[i] > 0:
        u.setdefault("unl", {})[i] = 1
        u.setdefault("lic", {})[i] = 1
    await update.message.reply_text(f"✅ {u['name']} / {E((D['resources'] | D['equipment'] | D['buildings'])[i]['name'])}: {d[i]:,}")


@adm
async def c_set(update, ctx, s, a):
    await setadd(update, a, False)


@adm
async def c_add(update, ctx, s, a):
    await setadd(update, a, True)


def adder(coll):
    @adm
    async def f(update, ctx, s, a):
        parts = [x.strip() for x in s.split("|")]
        i = nid()
        D[coll][i] = {"id": i, "name": parts[0], "initial": int(parts[1] or 0) if len(parts) > 1 else 0}
        if coll == "equipment":
            c = int(parts[2]) if len(parts) > 2 else classify(parts[0])
            if c is not None:
                D[coll][i]["cat"] = c
        await update.message.reply_text(f"✅ شناسه: {i}")
    return f


@adm
async def c_addb(update, ctx, s, a):
    i = nid()
    D["buildings"][i] = {"id": i, "name": s, "levels": {"1": {"cost": [], "act": [], "out": []}}}
    await update.message.reply_text(f"✅ شناسه: {i}")


@adm
async def c_edit(update, ctx, s, a):
    i, rest = a[0], s.partition(" ")[2]
    k = kind(i)
    if k == "b":
        D["buildings"][i]["name"] = rest
    else:
        n, v = split_ni(rest)
        o = (D["resources"] if k == "r" else D["equipment"])[i]
        o["name"], o["initial"] = n, v
    await update.message.reply_text("✅")


@adm
async def c_del(update, ctx, s, a):
    i = a[0]
    k = kind(i)
    D[{"r": "resources", "e": "equipment", "b": "buildings"}[k]].pop(i)
    for u in D["users"].values():
        u[{"r": "res", "e": "eq", "b": "bld"}[k]].pop(i, None)
    await update.message.reply_text("✅ حذف شد.")


@adm
async def c_lvl(update, ctx, s, a):
    lines = update.message.text.split("\n")
    b, l = D["buildings"][a[0]], int(a[1])
    if l > 1 and str(l - 1) not in b["levels"]:
        raise ValueError
    d = b["levels"].setdefault(str(l), {"cost": [], "act": [], "out": []})
    for ln in lines[1:]:
        key, _, v = ln.partition(":")
        key = key.strip().lower()
        if key in d:
            acc = {}
            for ch in v.split(","):
                x = ch.split()
                if len(x) == 2 and kind(x[0]) in ("r", "e"):
                    acc[kind(x[0]) + ":" + x[0]] = acc.get(kind(x[0]) + ":" + x[0], 0) + int(x[1])
            d[key] = pairs(acc)
    await update.message.reply_text(f"✅ لول {l}: هزینه {items(d['cost'])} | فعالیت {items(d['act'])} | تولید {items(d['out'])}")


@adm
async def c_dellvl(update, ctx, s, a):
    b = D["buildings"][a[0]]
    if a[1] == "1" or str(int(a[1]) + 1) in b["levels"]:
        raise ValueError
    b["levels"].pop(a[1])
    await update.message.reply_text("✅")


@adm
async def c_activate(update, ctx, s, a):
    if a and a[0] not in D["users"]:
        raise ValueError
    await update.message.reply_text(await run_activation(ctx, a[0] if a else None))


@adm
async def c_warphoto(update, ctx, s, a):
    wt = WT[a[0].lower()]
    if a[1:] == ["off"]:
        D.setdefault("warpics", {}).pop(wt, None)
        return await update.message.reply_text("✅ حذف شد.")
    ctx.user_data["wp"] = a[0].lower()
    await update.message.reply_text(f"حالا عکس لشکرکشی {WNAME[wt]} را بفرستید (یا با کپشن «/warphoto {a[0]}»).")


@adm
async def c_unlock(update, ctx, s, a):
    u = D["users"][a[0]]
    codes = list(D["buildings"]) if a[1:] == ["all"] else [c for c in a[1:] if c in D["buildings"]]
    if not codes:
        raise ValueError
    for c in codes:
        u.setdefault("unl", {})[c] = 1
    names = "\n".join("• " + E(D["buildings"][c]["name"]) for c in codes[:30]) + ("\n…" if len(codes) > 30 else "")
    await update.message.reply_text(f"✅ {len(codes)} ساختمان برای {uname(u)} باز شد.")
    await dm(ctx, u, f"🔓 ساختمان‌های جدید برای شما باز شد ({len(codes)}):\n{names}\nاز بخش 🏗 ساختمان‌ها آن‌ها را با تکنولوژی فعال کنید.")


@adm
async def c_lock(update, ctx, s, a):
    u = D["users"][a[0]]
    codes = list(u.get("unl", {})) if a[1:] == ["all"] else a[1:]
    for c in codes:
        u.get("unl", {}).pop(c, None)
    await update.message.reply_text(f"✅ {len(codes)} ساختمان برای {uname(u)} قفل شد.")


@adm
async def c_tech(update, ctx, s, a):
    tk = next(i for i, r in D["resources"].items() if "تکنولوژی" in r["name"])
    D["buildings"][a[0]]["unlock"] = [{"k": "r:" + tk, "amt": int(a[1])}]
    await update.message.reply_text("✅")


@adm
async def c_binfo(update, ctx, s, a):
    b = D["buildings"][a[0]]
    t = f"<code>{b['id']}</code> <b>{E(b['name'])}</b> · {cname(b.get('cat', '99'))}\n🔬 {items(b.get('unlock', []))}"
    for l, d in sorted(b["levels"].items(), key=lambda x: int(x[0])):
        t += f"\n\nلول {l}\nهزینه: {items(d['cost'])}\nمصرف: {items(d['act'])}\nتولید: {items(d['out'])}"
    await update.message.reply_text(t[:4000])


async def c_start(update, ctx):
    ctx.user_data.clear()
    if isadmin(update):
        return await update.message.reply_text("🛠 <b>پنل ادمین</b>", reply_markup=M(AMENU))
    u = me(update)
    if u:
        return await home(update, u)
    await update.message.reply_text("شما هنوز ثبت نشده‌اید. به ادمین بگویید یوزرنیم تلگرام شما را اضافه کند.\n\n" + who_am_i(update))


async def c_id(update, ctx):
    await update.message.reply_text(who_am_i(update))


async def c_help(update, ctx):
    if isadmin(update):
        await update.message.reply_text("\n\n".join(HELP.values()))


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    fid, cap = m.photo[-1].file_id, (m.caption or "").strip()
    if isadmin(update):
        a = cap.split()
        if cap.startswith("/warphoto") and len(a) > 1:
            wt = WT.get(a[1].lower())
        elif not cap.startswith("/photo"):
            wt = WT.get(ctx.user_data.get("wp", ""))
        else:
            wt = None
        if wt:
            ctx.user_data.pop("wp", None)
            D.setdefault("warpics", {})[wt] = fid
            save()
            return await m.reply_text(f"✅ عکس لشکرکشی {WNAME[wt]} تنظیم شد.")
        pid = a[1] if cap.startswith("/photo") and len(a) > 1 else ctx.user_data.pop("ph", None)
        if pid in D["users"]:
            D["users"][pid]["pic"] = fid
            save()
            await m.reply_text("✅ عکس پروفایل تنظیم شد.")
        return
    u, st = me(update), ctx.user_data.get("st")
    await publish_media(update, ctx, u, st, cap, photo=fid)


async def publish_media(update, ctx, u, st, cap, photo=None, video=None):
    if u and st and st.get("await") == "text" and st["k"] in ("decl", "chat"):
        head = uname(u) + (" — 📜 <b>بیانیه</b>" if st["k"] == "decl" else "")
        await post(ctx, CHANNEL_1, head + (f"\n\n{E(cap[:800])}" if cap else ""), photo=photo, video=video)
        D["messages"].append({"uid": u["id"], "kind": st["k"], "text": cap or ("🖼" if photo else "🎬")})
        save()
        ctx.user_data.clear()
        await show(update, "✅ منتشر شد.", [HOME])


async def on_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    await publish_media(update, ctx, me(update), ctx.user_data.get("st"), (m.caption or "").strip(), video=m.video.file_id)


@adm
async def c_photo(update, ctx, s, a):
    if len(a) > 1 and a[1] == "off":
        D["users"][a[0]].pop("pic", None)
        return await update.message.reply_text("✅ عکس حذف شد.")
    D["users"][a[0]]
    ctx.user_data["ph"] = a[0]
    await update.message.reply_text("حالا عکس را بفرستید (یا عکس را با کپشن «/photo شناسه» بفرستید).")


@adm
async def c_cat(update, ctx, s, a):
    e, n = D["equipment"][a[0]], int(a[1])
    if not 0 <= n < len(CATS):
        raise ValueError
    e["cat"] = n
    await update.message.reply_text(f"✅ {E(e['name'])} ← {CATS[n]}")


@adm
async def c_cats(update, ctx, s, a):
    await update.message.reply_text("\n".join(f"{i}. {c}" for i, c in enumerate(CATS)))


async def on_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    a = q.data.split(":")
    try:
        if a[0] == "x":
            pass
        elif a[0] == "A":
            if isadmin(update):
                await a_cb(update, ctx, a[1:])
        else:
            u = me(update)
            if u:
                await p_cb(update, ctx, u, a)
        await q.answer()
    except (ValueError, KeyError) as e:
        await q.answer(str(e) if isinstance(e, ValueError) else "خطا", show_alert=True)


def main():
    b = Application.builder().token(BOT_TOKEN).defaults(Defaults(parse_mode="HTML"))
    b = b.connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
    b = b.get_updates_connect_timeout(30).get_updates_read_timeout(30).get_updates_write_timeout(30).get_updates_pool_timeout(30)

    app = b.build()
    for n, f in [("start", c_start), ("menu", c_start), ("help", c_help), ("warphoto", c_warphoto), ("activate", c_activate), ("unlock", c_unlock), ("lock", c_lock), ("tech", c_tech), ("binfo", c_binfo), ("photo", c_photo), ("cat", c_cat), ("cats", c_cats), ("id", c_id), ("addplayer", c_addplayer), ("delplayer", c_delplayer),
                 ("name", c_name), ("flag", c_flag), ("set", c_set), ("add", c_add), ("addres", adder("resources")),
                 ("addeq", adder("equipment")), ("addb", c_addb), ("edit", c_edit), ("del", c_del), ("lvl", c_lvl), ("dellvl", c_dellvl)]:
        app.add_handler(CommandHandler(n, f))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.VIDEO, on_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
