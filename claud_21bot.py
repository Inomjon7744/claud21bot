import asyncio
import logging
import re
from collections import deque
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

BOT_TOKEN = "7989529698:AAGog-G1HpDKwFe2SMud38xpi811Y0QLsQg"
CHANNEL = "@statistika_21f"
CHECK_INTERVAL = 30
MAX_GAMES = 50

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
games_history = deque(maxlen=MAX_GAMES)
last_game_id = 0
watching_users = set()

def parse_game(text):
    match = re.search(r'#N(\d+)\.\s*(\d+)\(([^)]+)\)\s*-\s*(\d+)\(([^)]+)\)', text)
    if not match:
        return None
    n = int(match.group(1))
    p1 = int(match.group(2))
    p1c = match.group(3)
    p2 = int(match.group(4))
    p2c = match.group(5)
    t = re.search(r'#T(\d+)', text)
    total = int(t.group(1)) if t else p1+p2
    if p1==p2: w=0
    elif p1>21 and p2>21: w=0
    elif p1>21: w=2
    elif p2>21: w=1
    elif p1==21: w=1
    elif p2==21: w=2
    elif p1>p2: w=1
    else: w=2
    return {'n':n,'p1':p1,'p2':p2,'p1c':p1c,'p2c':p2c,'total':total,'w':w}

def predict(games):
    if len(games)<3: return None
    last=games[-1]['w']
    streak=1
    for g in reversed(games[:-1]):
        if g['w']==last: streak+=1
        else: break
    p1=sum(1 for g in games[-10:] if g['w']==1)
    p2=sum(1 for g in games[-10:] if g['w']==2)
    wl={1:"1-o'yinchi 🟦",2:"2-o'yinchi 🟥",0:"Durang ⬜"}
    if streak>=3 and last in [1,2]:
        pred=2 if last==1 else 1
        conf="Yuqori 🔥"
        reason=f"{streak} ketma-ket — o'zgarish kutilmoqda"
    elif p1>p2+1:
        pred=1; conf="O'rta ⚡"; reason="So'nggi 10 da 1-o'yinchi kuchli"
    elif p2>p1+1:
        pred=2; conf="O'rta ⚡"; reason="So'nggi 10 da 2-o'yinchi kuchli"
    else:
        pred=1 if p1>=p2 else 2; conf="Past ⚪"; reason="Umumiy statistika"
    return {'pred':pred,'conf':conf,'reason':reason,'streak':streak,'last':last,'wl':wl}

async def fetch():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://t.me/s/statistika_21f",timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status==200:
                    html=await r.text()
                    msgs=re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',html,re.DOTALL)
                    clean=[]
                    for m in msgs:
                        m=re.sub(r'<[^>]+>','',m).strip()
                        if '#N' in m and '(' in m: clean.append(m)
                    return clean
    except: pass
    return []

async def monitor():
    global last_game_id
    while True:
        try:
            if watching_users:
                msgs=await fetch()
                new=[]
                for m in msgs:
                    g=parse_game(m)
                    if g and g['n']>last_game_id: new.append(g)
                new.sort(key=lambda x:x['n'])
                for g in new:
                    games_history.append(g)
                    last_game_id=g['n']
                    pr=predict(list(games_history))
                    if pr:
                        wl=pr['wl']
                        avg=sum(x['total'] for x in games_history)/len(games_history)
                        text=(f"🃏 *#N{g['n']} tugadi!*\n"
                              f"`{g['p1']}({g['p1c']}) — {g['p2']}({g['p2c']})`\n"
                              f"✅ G'olib: {wl.get(g['w'],'?')}\n"
                              f"📊 Total: #{g['total']}\n\n"
                              f"🎯 *KEYINGI #N{g['n']+1} TAXMINI:*\n"
                              f"👉 *{wl.get(pr['pred'],'?')}*\n"
                              f"💡 {pr['conf']} — {pr['reason']}\n"
                              f"📈 O'rtacha total: {avg:.1f}\n"
                              f"⏱ {datetime.now().strftime('%H:%M:%S')}")
                        for uid in list(watching_users):
                            try: await bot.send_message(uid,text,parse_mode="Markdown")
                            except: watching_users.discard(uid)
        except Exception as e: logging.error(e)
        await asyncio.sleep(CHECK_INTERVAL)

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🃏 *21 Ochko Tahlil Bot*\n\n/watch — boshlash\n/stop — to'xtatish\n/stats — statistika",parse_mode="Markdown")

@dp.message(Command("watch"))
async def watch(m: types.Message):
    watching_users.add(m.from_user.id)
    await m.answer("✅ Kuzatish boshlandi! Har 30 soniyada tekshiraman 🎯")

@dp.message(Command("stop"))
async def stop(m: types.Message):
    watching_users.discard(m.from_user.id)
    await m.answer("⏹ To'xtatildi.")

@dp.message(Command("stats"))
async def stats(m: types.Message):
    if len(games_history)<2:
        await m.answer("Hali ma'lumot yo'q. /watch bosing.")
        return
    g=list(games_history)
    p1=sum(1 for x in g if x['w']==1)
    p2=sum(1 for x in g if x['w']==2)
    pr=predict(g)
    wl=pr['wl'] if pr else {}
    await m.answer(f"📊 *{len(g)} o'yin*\n🟦 1-o'yinchi: {p1}\n🟥 2-o'yinchi: {p2}\n\n🎯 Taxmin: {wl.get(pr['pred'],'?') if pr else '?'}",parse_mode="Markdown")

async def main():
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
