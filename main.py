import config, random, datetime, threading, time, schedule, asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher.filters import builtin

bot = Bot(config.TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class PlanStatesGroup(StatesGroup):
    adding_wish = State()
    adding_wishes = State()
    comparing_wishes = State()

class AdminSatesGroup(StatesGroup):
    setting_ad_message = State()
    setting_message_for_everyone = State()
    checking_message_for_everyone = State()
    setting_message_for_user = State()
    checking_message_for_user = State()
    setting_message_for_admins = State()
    checking_message_for_admins = State()

def sched_run(interval: int = 1):
    stop_sched = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not stop_sched.is_set():
                schedule.run_pending()
                time.sleep(interval)
    
    sched_thread_run = ScheduleThread()
    sched_thread_run.start()
    return stop_sched
            
def clear_stat_daily():
    config.stat_daily_users_viewed_ad.clear()
    config.stat_daily_ad_views = config.stat_daily_added_users = 0
    curtime = datetime.datetime.now()
    print(f'[{getcurdatetime(curtime)}] Daily statistics have been cleared. New day!)\n')

def clear_stat_month():
    config.stat_month_users_viewed_ad.clear()
    config.stat_month_ad_views = config.stat_month_added_users = 0
    curtime = datetime.datetime.now()
    print(f'[{getcurdatetime(curtime)}] Month statistics have been cleared. New month!)\n')

async def send_admins(message: types.Message):
    for id in config.Admins:
        await message.send_copy(id)

def getcurdatetime(curtime: datetime.datetime):
    day = curtime.day if curtime.day >= 10 else '0' + str(curtime.day)
    month = curtime.month if curtime.month >= 10 else '0' + str(curtime.month)
    hour = curtime.hour if curtime.hour >= 10 else '0' + str(curtime.hour)
    minute = curtime.minute if curtime.minute >= 10 else '0' + str(curtime.minute)
    return f'{day}.{month}.{curtime.year} {hour}:{minute}'

@dp.message_handler(commands=['cancel'], state='*')
async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
    await state.finish()
    await message.reply(config.CANCEL_TEXT)

async def delete_messages(state: FSMContext):
    async with state.proxy() as data:
        for mess_id in data['mess_to_delete']:
            await bot.delete_message(data['chat_id'], mess_id)
        data['mess_to_delete'].clear()

async def on_startup(disp: Dispatcher):
    with open('admins.txt', 'r') as f:
        config.Admins = [int(id) for id in f.readlines()]
        f.close()

    with open('users.txt', 'r') as f:
        config.stat_users = len(f.readlines())

    schedule.every().day.at(config.TIME_TO_CLEAR_STAT).do(clear_stat_daily) # every day
    schedule.every(30).days.at(config.TIME_TO_CLEAR_STAT).do(clear_stat_month) # every month
    config.stop_sched_flag = sched_run()

    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] Bot was started successfuly.")
    msg = types.Message(text='Бот успешно запущен!')
    await send_admins(msg)

async def on_shutdown(disp: Dispatcher):
    config.stop_sched_flag.set()
    await asyncio.sleep(1)

    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] Bot was shut down successfuly.")
    msg = types.Message(text='Бот успешно остановлен.')
    await send_admins(msg)

async def find_user(id):
    with open('users.txt', 'r') as f:
        while True:
            line = f.readline()
            if line == '':
                break
            if str(id) in line:
                f.close()
                return True
    return False

async def insert_user(id: int, username: str):
    if await find_user(id) == True:
        return True
    with open('users.txt', 'a') as f:
        curtime = datetime.datetime.now()
        f.write(f"{id} {getcurdatetime(curtime)} {username} 0\n")
        f.close()
    config.stat_daily_added_users += 1
    config.stat_month_added_users += 1
    config.stat_users += 1
    return False

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    if await insert_user(message.from_user.id, message.from_user.username) == True:
        await message.answer(config.OLD_HELLO_TEXT.replace('__user__', message.from_user.first_name), reply_markup=config.plan_kb)
    else:
        await message.answer(config.NEW_HELLO_TEXT.replace('__user__', message.from_user.first_name), reply_markup=config.help_kb)

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['help'])
async def help_admins(message: types.Message) -> None:
    await message.answer(config.HELP_FOR_ADMINS_TEXT)

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message) -> None:
    await message.answer(config.HELP_TEXT, reply_markup=config.plan_kb)

@dp.message_handler(commands=['show_ad'])
async def show_ad(message: types.Message) -> None:
    await config.AD_MESSAGE.send_copy(message.from_id)
    config.stat_daily_ad_views += 1
    config.stat_daily_users_viewed_ad.add(message.from_user.id)
    config.stat_month_ad_views += 1
    config.stat_month_users_viewed_ad.add(message.from_user.id)

@dp.message_handler(commands=['stat', 'statistics'])
async def show_stat(message: types.Message):
    await message.answer(text=config.STAT_MESSAGE_TEXT.format(config.stat_users, config.TIME_TO_CLEAR_STAT, config.stat_daily_added_users, config.stat_daily_ad_views, len(config.stat_daily_users_viewed_ad),
                                                              config.stat_month_added_users, config.stat_month_ad_views, len(config.stat_month_users_viewed_ad),
                                                              (config.stat_month_added_users + 29) // 30, (config.stat_month_ad_views + 29) // 30, (len(config.stat_month_users_viewed_ad) + 29) // 30))

@dp.callback_query_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.checking_message_for_everyone)
async def check_msgforevrn(callback: types.CallbackQuery, state: FSMContext):
    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] sending message to everyone:", end='\n\t\t   ')
    if callback.data == 'send':
        async with state.proxy() as data:
            with open('users.txt', 'r') as f:
                s = f.readline()
                while s:
                    await data['message'].send_copy(s.split()[0])
                    s = f.readline()
                f.close()
        await callback.answer(config.MESSAGE_SEND_SUCCESSUFLY_TEXT, show_alert=True)
        print('Message sent successfuly.')
    else:
        await callback.answer(config.CANCEL_TEXT, show_alert=True)
        print('Sending message canceled.')
    await state.finish()

@dp.message_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.setting_message_for_everyone, content_types='any')
async def set_msgforevrn(message: types.Message, state: FSMContext):
    await AdminSatesGroup.next()
    async with state.proxy() as data:
        data['message'] = message
    await message.reply(config.CHECK_MESSAGE_TEXT.format('всем пользователям бота'), reply_markup=config.check_message_ikb)

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['sendeveryone'])
async def send_everyone(message: types.Message):
    await message.answer(config.INVITE_SET_MESSAGE_TEXT)
    await AdminSatesGroup.setting_message_for_everyone.set()

@dp.callback_query_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.checking_message_for_user)
async def check_msgforusr(callback: types.CallbackQuery, state: FSMContext):
    curtime = datetime.datetime.now()
    async with state.proxy() as data:
        print(f'[{getcurdatetime(curtime)}] sending message to user {data["id"]}:', end='\n\t\t   ')
    if callback.data == 'send':
        async with state.proxy() as data:
            await data['message'].send_copy(data['id'])
        await callback.answer(config.MESSAGE_SEND_SUCCESSUFLY_TEXT, show_alert=True)
        print('Message sent successfuly.')
    else:
        await callback.answer(config.CANCEL_TEXT, show_alert=True)
        print('Sending message canceled')
    await state.finish()

@dp.message_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.setting_message_for_user, content_types='any')
async def set_msgforusr(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        id = data['id']
    await AdminSatesGroup.next()
    async with state.proxy() as data:
        data['message'] = message
        data['id'] = id
    await message.reply(config.CHECK_MESSAGE_TEXT.format(f'пользователю с id {id}'), reply_markup=config.check_message_ikb)

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['send'])
async def send_user(message: types.Message, state: FSMContext):
    if len(message.text.split()) != 2:
        await message.reply(config.ERROR_SEND_CHECKING_USER_TEXT.replace('__ERROR__', 'неверное количество агрументов'))
        return
    id = message.text.split()[1]
    if not id.isdigit():
        await message.reply(config.ERROR_SEND_CHECKING_USER_TEXT.replace('__ERROR__', 'неверный id'))
        return
    if not await find_user(id):
        await message.reply(config.ERROR_SEND_CHECKING_USER_TEXT.replace('__ERROR__', 'такого пользователя нету'))
        return
    await message.answer(config.INVITE_SET_MESSAGE_TEXT)
    await AdminSatesGroup.setting_message_for_user.set()
    async with state.proxy() as data:
        data['id'] = id

@dp.callback_query_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.checking_message_for_admins)
async def check_msgforadmns(callback: types.CallbackQuery, state: FSMContext):
    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] sending message to admins:", end='\n\t\t   ')
    if callback.data == 'send':
        async with state.proxy() as data:
            await send_admins(data['message'])
        await callback.answer(config.MESSAGE_SEND_SUCCESSUFLY_TEXT, show_alert=True)
        print('Message sent successfuly.')
    else:
        await callback.answer(config.CANCEL_TEXT, show_alert=True)
        print('Sending message canceled.')
    await state.finish()

@dp.message_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.setting_message_for_admins, content_types='any')
async def set_msgforadmns(message: types.Message, state: FSMContext):
    await AdminSatesGroup.next()
    async with state.proxy() as data:
        data['message'] = message
    await message.reply(config.CHECK_MESSAGE_TEXT.format('администраторам бота'), reply_markup=config.check_message_ikb)

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['send_admins'])
async def send_admins_cmd(message: types.Message):
    await message.answer(config.INVITE_SET_MESSAGE_TEXT)
    await AdminSatesGroup.setting_message_for_admins.set()

@dp.message_handler(commands=['plan'])
async def cmd_plan(message: types.Message, state: FSMContext) -> None:
    mess = await message.answer(config.PLAN_TEXT + "\nВы пока не указали ваши желания.", reply_markup=config.plan_ikb)
    async with state.proxy() as data:
        data.clear()
        data['size'] = 0
        data['wishes_list_mess_id'] = mess.message_id
        data['chat_id'] = message.chat.id
        data['wishes_added'] = False
        data['mess_to_delete'] = []
    await PlanStatesGroup.adding_wishes.set()

async def cmp_wishes(state: FSMContext, ind1=-1, ind2=-1):
    if ind1 == -1:
        ind1 = random.randint(0, len(config.GOOD_TEXTS) - 1)
    if ind2 == -1:
        ind2 = random.randint(0, len(config.COMPARE_START_TEXTS) - 1)
    async with state.proxy() as data:
        first = data[str(data['order_cmp'][data['pos']][0])]
        second = data[str(data['order_cmp'][data['pos']][1])]
        # first = first[0].lower() + first[1:len(first)]
        # second = second[0].lower() + second[1:len(second)]
        text = config.COMPARE_TEXT.format(config.GOOD_TEXTS[ind1], config.COMPARE_START_TEXTS[ind2], first, second)
        mess = await bot.send_message(chat_id=data['chat_id'], text=text, reply_markup=await config.get_cmp_ikb(data[str(data['order_cmp'][data['pos']][0])], 
                                                                                                          data[str(data['order_cmp'][data['pos']][1])]))
        data['compare_mess_id'] = mess.message_id

@dp.callback_query_handler(state=PlanStatesGroup.adding_wishes)
async def add_wishes_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'add_wish':
        async with state.proxy() as data:
            if data['size'] == config.MAX_AMOUNT_OF_WISHES:
                await callback.answer(text=config.TOO_MANY_WISHES_TEXT, show_alert=True)
                return
            mess = await bot.send_message(chat_id=data['chat_id'], text=config.ADD_WISH_TEXT, reply_markup=config.add_wish_cancel_ikb)
            data['mess_to_delete'].append(mess.message_id)
            data['wish_added'] = False
        await PlanStatesGroup.adding_wish.set()
    else:
        async with state.proxy() as data:
            if data['wishes_added'] == True:
                return
            if data['size'] < 2:
                await callback.answer(config.TOO_FEW_WISHES_TEXT, show_alert=True)
                return
            data['wishes_added'] = True
            mess = await bot.send_message(chat_id=data['chat_id'], text=config.INVITE_COMPARE_TEXT)
            data['invite_compare_mess_id'] = mess.message_id
            data['order_cmp'] = []
            for i in range(1, data['size']):
                data['count_+'] = [0 for _ in range(data['size'])]
                for j in range(i + 1, data['size'] + 1):
                    if random.randint(0, 1) == 0:
                        data['order_cmp'].append([i, j])
                    else:
                        data['order_cmp'].append([j, i])
            random.shuffle(data['order_cmp'])
            data['pos'] = 0
            data['compare_mess_id'] = None
        await cmp_wishes(state, 0)
        await PlanStatesGroup.next()

@dp.callback_query_handler(state=PlanStatesGroup.adding_wish)
async def add_wish_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'cancel':
        await callback.answer(text=config.CANCEL_TEXT, show_alert=True)
        await delete_messages(state)
        async with state.proxy() as data:
            data['wish_added'] = True
        await PlanStatesGroup.next()

async def myformat(s: str):
    res = ''
    for ch in s:
        if ch.isalpha() or ch.isdigit():
            res = '*'
            break
    if res == '':
        return ''
    i = 0
    while i < len(s):
        if s[i] == '\n':
            s = s[0:i]
            break
        if not s[i].isalpha() and not s[i].isascii():
            s = s[0:i] + s[i + 1:len(s)]
        else:
            i += 1
    i = len(s) - 1
    while i >= 0 and s[i] in '.,!?':
        i -= 1
    if i == -1:
        return ''
    res = s[0:i + 1]
    return res

@dp.message_handler(state=PlanStatesGroup.adding_wishes)
async def add_wish_(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        mess = await message.answer(text=config.BUTTON_CLICK_TEXT)
        data['mess_to_delete'].append(mess.message_id)
        data['mess_to_delete'].append(message.message_id)

@dp.message_handler(state=PlanStatesGroup.adding_wish)
async def add_wish(message: types.Message, state: FSMContext):
    text = await myformat(message.text)
    async with state.proxy() as data:
        if len(text) == 0:
            mess = await message.answer(text=config.CORRECT_TEXT)
            data['mess_to_delete'].append(mess.message_id)
            data['mess_to_delete'].append(message.message_id)
            return
        text = text[0].upper() + text[1:len(text)]
        for i in range(data['size']):
            if data[str(i + 1)] == text:
                mess = await message.answer(text=config.SAME_WISHES_TEXT)
                data['mess_to_delete'].append(mess.message_id)
                data['mess_to_delete'].append(message.message_id)
                return
        data['size'] += 1
        data[str(data['size'])] = text
        await message.delete()
    await delete_messages(state)
    async with state.proxy() as data:
        text = config.PLAN_TEXT
        for i in range(1, data['size'] + 1):
            text += f"\n{i}) {data[str(i)]}"
        await bot.edit_message_text(text=text, chat_id=data['chat_id'], message_id=data['wishes_list_mess_id'], reply_markup=config.plan_ikb)
    await PlanStatesGroup.adding_wishes.set()

async def show_results(state: FSMContext):
    async with state.proxy() as data:
        result = [[data['count_+'][i], i] for i in range(data['size'])]
        result.sort(key=lambda x: -x[0])
        text = config.SHOW_RESULT_TEXT
        for i in range(1, data['size'] + 1):
            text += f"\n{i}) {data[str(result[i - 1][1] + 1)]}"
        await bot.send_message(chat_id=data['chat_id'], text=text)
        if config.MODE == config.Modes.no_ad_mode.value:
            return
        if config.MODE == config.Modes.your_ad_mode.value:
            await bot.send_message(chat_id=data['chat_id'], text=config.YOUR_AD_TEXTS[random.randint(0, len(config.YOUR_AD_TEXTS) - 1)])
        elif config.MODE == config.Modes.ad_mode.value:
            await config.AD_MESSAGE.send_copy(data['chat_id'])
        config.stat_daily_ad_views += 1
        config.stat_daily_users_viewed_ad.add(data['chat_id'])
        config.stat_month_ad_views += 1
        config.stat_month_users_viewed_ad.add(data['chat_id'])

@dp.message_handler(state=PlanStatesGroup.comparing_wishes)
async def _compare_wishes(message: types.Message):
    await message.delete()

@dp.callback_query_handler(state=PlanStatesGroup.comparing_wishes)
async def compare_wishes(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        first = data['order_cmp'][data['pos']][0]
        second = data['order_cmp'][data['pos']][1]
        sz, pos = len(data['order_cmp']), data['pos']
    if callback.data == 'first':
        async with state.proxy() as data:
            data['count_+'][first - 1] += 1
    else:
        async with state.proxy() as data:
            data['count_+'][second - 1] += 1
    if pos < sz - 1:
        async with state.proxy() as data:
            data['pos'] += 1
            await bot.delete_message(chat_id=data['chat_id'], message_id=data['compare_mess_id'])
        await cmp_wishes(state)
    else:
        await bot.delete_message(chat_id=data['chat_id'], message_id=data['compare_mess_id'])
        await bot.delete_message(chat_id=data['chat_id'], message_id=data['invite_compare_mess_id'])
        await show_results(state)
        await state.finish()
    
@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['change_ad'])
async def change_ad(message: types.Message, state: FSMContext):
    await message.answer(text=config.INVITE_SET_AD_MESSAGE_TEXT)
    await AdminSatesGroup.setting_ad_message.set()
    async with state.proxy() as data:
        data['mess_to_delete'] = []

@dp.message_handler(lambda message: message.from_user.id in config.Admins, state=AdminSatesGroup.setting_ad_message, content_types='any')
async def set_ad_message(message: types.Message, state: FSMContext):
    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] New ad was set successfuly.\n\t\t   You can see it by /show_ad command")
    config.AD_MESSAGE = message
    await message.reply(config.AD_SET_SUCCESSFULY_TEXT)
    await delete_messages(state)
    await state.finish()

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['set_mode'])
async def set_mode_cmd(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['mess_to_delete'] = []
    curtime = datetime.datetime.now()
    print(f"[{getcurdatetime(curtime)}] command /set_mode:", end='\n\t\t   ')
    mode = message.text.split()
    if len(mode) != 2 or not mode[1].isdigit():
        print("Error setting mode: bad args.")
        async with state.proxy() as data:
            mess = await message.reply(text=config.ERROR_SETTING_MODE_TEXT)
            data['mess_to_delete'].append(mess.message_id)
            data['mess_to_delete'].append(message.message_id)
        return
    mode = int(mode[1])
    config.MODE = mode
    if mode == config.Modes.no_ad_mode.value: # TODO
        print(f"Set mode {config.Modes.no_ad_mode.value}. The bot won't show any ad from now.")
    elif mode == config.Modes.your_ad_mode.value:
        print(f"Set mode {config.Modes.your_ad_mode.value}. The bot will show an invitation for your ad from now.")
    elif mode == config.Modes.ad_mode.value:
        print(f"Set mode {config.Modes.ad_mode.value}. The bot will show an ad from now.")
    else:
        print("Error setting mode: mode number was not in good range.")
        async with state.proxy() as data:
            mess = await message.reply(text=config.ERROR_SETTING_MODE_TEXT)
            data['mess_to_delete'].append(mess.message_id)
            data['mess_to_delete'].append(message.message_id)
        return
    await delete_messages(state)
    await message.answer(config.MODE_SET_SUCCESSFULY_TEXT.replace("__MODE__", config.MODES_TEXTS[config.MODE]))

@dp.message_handler(lambda message: message.from_user.id in config.Admins, commands=['admins'])
async def admins_list(message: types.Message):
    text = config.ADMINS_LIST_TEXT
    for i in range(len(config.Admins)):
        text += f'{i + 1}) {config.Admins[i]}\n'
    await message.answer(text)

@dp.message_handler(commands=['add_admin'], user_id=config.root)
async def add_admin(message: types.Message):
    if len(message.text.split()) != 2:
        await message.reply(text=config.ERROR_ADDING_ADMIN_TEXT.replace('__ERROR__', 'неверное количество аргументов'))
        return
    id = message.text.split()[1]
    if not id.isdigit():
        await message.reply(text=config.ERROR_ADDING_ADMIN_TEXT.replace('__ERROR__', 'неверный id нового админа'))
        return
    if int(id) in config.Admins:
        await message.reply(text=config.ERROR_ADDING_ADMIN_TEXT.replace('__ERROR__', 'такой админ уже есть'))
        return
    with open('admins.txt', 'a') as f:
        f.write(id + '\n')
        f.close()
    config.Admins.append(int(id))
    await message.reply(text=config.ADMIN_ADDED_SUCCESSFULY_TEXT)
    await bot.send_message(int(id), text=config.YOU_ARE_NEW_ADMIN_TEXT)
    curtime = datetime.datetime.now()
    print(f'[{getcurdatetime(curtime)}] admin {id} was added successfuly.')
    return

@dp.message_handler(commands=['del_admin'], user_id=config.root)
async def del_admin(message: types.message):
    if len(message.text.split()) != 2:
        await message.reply(text=config.ERROR_DELETING_ADMIN_TEXT.replace('__ERROR__', 'неверное количество аргументов'))
        return
    id = message.text.split()[1]
    if not id.isdigit():
        await message.reply(text=config.ERROR_DELETING_ADMIN_TEXT.replace('__ERROR__', 'неверный id админа'))
        return
    id = int(id)
    for i in range(len(config.Admins)):
        if config.Admins[i] == id:
            config.Admins = config.Admins[0:i] + config.Admins[i + 1:]
            with open('admins.txt', 'r+') as f:
                for _ in range(i - 1):
                    f.readline()
                pos = f.tell()
                f.readline()
                s = f.read()
                f.seek(pos)
                f.truncate()
                f.write(s)
            await message.reply(text=config.ADMIN_DELETED_SUCCESSFULY_TEXT)
            await bot.send_message(id, text=config.YOU_ARE_NOT_ADMIN_NOW_TEXT)
            curtime = datetime.datetime.now()
            print(f'[{getcurdatetime(curtime)}] admin {id} was deleted successfuly.')
            return
    await message.reply(text=config.ERROR_DELETING_ADMIN_TEXT.replace('__ERROR__', 'такого админа нету'))
    return

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
