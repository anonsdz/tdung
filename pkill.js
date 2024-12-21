const { exec } = require('child_process');
const { Telegraf } = require('telegraf');
const os = require('os');
const osu = require('os-utils');

// Khởi tạo bot Telegram
const bot = new Telegraf('7584086130:AAEuGKtQuKvWKOC2sLIvVOnS7v93QsLViiM'); 
const chatId = '7371969470'; 

// Ngưỡng cảnh báo
const NGUONG_CPU = 90;
const NGUONG_RAM = 90;

let soLanPkill = 0;  // Biến lưu số lần thực hiện pkill

// Kiểm tra nếu tiến trình có tồn tại
const kiemTraTienTrinh = (tenTienTrinh) => new Promise((resolve) => {
    exec(`pgrep -f ${tenTienTrinh}`, (error) => resolve(!error));
});

// Hàm kiểm tra và thực thi pkill
const kiemTraVaThucThiPkill = async () => {
    const tienTrinh = ['flood', 'tlskill', 'bypass', 'killer'];

    for (const tienTrinhItem of tienTrinh) {
        const tonTai = await kiemTraTienTrinh(tienTrinhItem);
        if (tonTai) {
            exec(`pkill -9 -f ${tienTrinhItem}`, (err) => {
                if (!err) {
                    soLanPkill++;
                    console.log(`Đã thực thi pkill cho ${tienTrinhItem}`);
                } else {
                    console.error(`Lỗi khi thực thi pkill cho ${tienTrinhItem}`);
                }
            });
        }
    }
};

// Hàm lấy thông tin hệ thống chi tiết
const layThongTinHeThong = () => new Promise((resolve) => {
    const tongRam = os.totalmem() / (1024 ** 3); // Tổng RAM (GB)
    const ramTruoc = os.freemem() / (1024 ** 3); // RAM trống (GB)
    const ramDaSuDung = tongRam - ramTruoc; // RAM đã dùng (GB)
    const tongCore = os.cpus().length; // Tổng số lõi CPU
    const cpuModel = os.cpus()[0].model; // Model CPU
    const uptime = (os.uptime() / 3600).toFixed(2); // Thời gian chạy (giờ)
    const osType = os.type(); // Loại hệ điều hành (Linux, Darwin, Windows, ...)
    const osRelease = os.release(); // Phiên bản hệ điều hành
    const osPlatform = os.platform(); // Nền tảng (linux, darwin, win32, ...)

    osu.cpuUsage(tyLeCpu => {
        resolve({
            tongRam: tongRam.toFixed(2),
            ramDaSuDung: ramDaSuDung.toFixed(2),
            ramTruoc: ramTruoc.toFixed(2),
            tyLeCpu: (tyLeCpu * 100).toFixed(2),
            tongCore,
            cpuModel,
            uptime,
            osType,
            osRelease,
            osPlatform
        });
    });
});

// Hàm chạy speedtest-cli
const chaySpeedTest = () => new Promise((resolve) => {
    exec('speedtest-cli --secure --json', (error, stdout, stderr) => {
        if (error) {
            resolve({ ping: 'N/A', download: 'N/A', upload: 'N/A' });  // Không gửi lỗi, trả về giá trị mặc định
        }
        try {
            const ketQua = JSON.parse(stdout);
            resolve({
                ping: ketQua.ping,
                download: (ketQua.download / 1e6).toFixed(2), // Mbps
                upload: (ketQua.upload / 1e6).toFixed(2)    // Mbps
            });
        } catch (err) {
            resolve({ ping: 'N/A', download: 'N/A', upload: 'N/A' });  // Nếu lỗi phân tích, trả về mặc định
        }
    });
});

// Lệnh "/start" để bắt đầu
bot.start(async (ctx) => {
    const tinNhanBanDau = await ctx.reply('Chào bạn! Tôi sẽ gửi thông tin hệ thống mỗi giây.');
    const messageId = tinNhanBanDau.message_id;

    setInterval(async () => {
        try {
            const thongTinHeThong = await layThongTinHeThong();
            const ketQuaSpeedTest = await chaySpeedTest();

            // Tính toán tài nguyên tổng đang sử dụng chỉ dựa trên CPU và RAM
            const taiNguyenTongSuDung = (
                parseFloat(thongTinHeThong.tyLeCpu) +
                (parseFloat(thongTinHeThong.ramDaSuDung) / parseFloat(thongTinHeThong.tongRam) * 100)
            ) / 2;  // Tính trung bình chỉ với CPU và RAM

            // Kiểm tra và thực hiện pkill nếu cần (chỉ kiểm tra CPU và RAM)
            if (
                parseFloat(thongTinHeThong.tyLeCpu) >= NGUONG_CPU ||
                parseFloat(thongTinHeThong.ramDaSuDung) >= NGUONG_RAM
            ) {
                await kiemTraVaThucThiPkill();

                const thongBaoCảnhBáo = `⚠️ **Cảnh báo: Quá tải tài nguyên!**\n\n` +
                    `💻 [Sử dụng CPU]: ${thongTinHeThong.tyLeCpu}%\n` +
                    `💾 [Bộ nhớ đã sử dụng]: ${thongTinHeThong.ramDaSuDung} GB\n` +
                    `🧠 [CPU còn lại]: ${(100 - thongTinHeThong.tyLeCpu).toFixed(2)}%\n` +
                    `🧳 [Bộ nhớ còn lại]: ${thongTinHeThong.ramTruoc} GB\n` +
                    `🔧 [Model CPU]: ${thongTinHeThong.cpuModel}\n` +
                    `🔲 [Số lõi CPU]: ${thongTinHeThong.tongCore}\n` +
                    `🌐 [Hệ điều hành]: ${thongTinHeThong.osType} ${thongTinHeThong.osRelease} (${thongTinHeThong.osPlatform})\n` +
                    `⏳ [Thời gian hoạt động]: ${thongTinHeThong.uptime} giờ\n\n` +
                    `📊 **Speed Test**:\n` +
                    `- 📶 [Ping]: ${ketQuaSpeedTest.ping} ms\n` +
                    `- ⚡️ [Tốc độ Download]: ${ketQuaSpeedTest.download} Mbps\n` +
                    `- ⬆️ [Tốc độ Upload]: ${ketQuaSpeedTest.upload} Mbps\n\n` +
                    `🔨 Tổng số lần thực hiện pkill: ${soLanPkill} [${taiNguyenTongSuDung.toFixed(2)}% tài nguyên hệ thống đang sử dụng]`;

                await ctx.telegram.sendMessage(chatId, thongBaoCảnhBáo);
            }

            // Cập nhật lại thông tin
            const thongTinCapNhat = `🔧 [Thông tin hệ thống và tốc độ mạng]:\n\n` +
                `💻 [Sử dụng CPU]: ${thongTinHeThong.tyLeCpu}%\n` +
                `💾 [Bộ nhớ đã sử dụng]: ${thongTinHeThong.ramDaSuDung} GB (${((thongTinHeThong.ramDaSuDung / thongTinHeThong.tongRam) * 100).toFixed(2)}%)\n` +
                `🧠 [CPU còn lại]: ${(100 - thongTinHeThong.tyLeCpu).toFixed(2)}%\n` +
                `🧳 [Bộ nhớ còn lại]: ${thongTinHeThong.ramTruoc} GB\n` +
                `🔧 [Model CPU]: ${thongTinHeThong.cpuModel}\n` +
                `🔲 [Số lõi CPU]: ${thongTinHeThong.tongCore}\n` +
                `🌐 [Hệ điều hành]: ${thongTinHeThong.osType} ${thongTinHeThong.osRelease} (${thongTinHeThong.osPlatform})\n` +
                `⏳ [Thời gian hoạt động]: ${thongTinHeThong.uptime} giờ\n\n` +
                `📊 **Speed Test**:\n` +
                `- 📶 [Ping]: ${ketQuaSpeedTest.ping} ms\n` +
                `- ⚡️ [Tốc độ Download]: ${ketQuaSpeedTest.download} Mbps\n` +
                `- ⬆️ [Tốc độ Upload]: ${ketQuaSpeedTest.upload} Mbps\n\n` +
                `🔨 Tổng số lần thực hiện pkill: ${soLanPkill} [${taiNguyenTongSuDung.toFixed(2)}% tài nguyên hệ thống đang sử dụng]`;

            await ctx.editMessageText(thongTinCapNhat, { chat_id: ctx.chat.id, message_id: messageId });

        } catch (err) {
            console.error(`Lỗi khi lấy thông tin: ${err}`);
        }
    }, 5000); // Cập nhật mỗi 5 giây
});

// Khởi chạy bot
bot.launch();
console.log('Bot đã chạy thành công!');
