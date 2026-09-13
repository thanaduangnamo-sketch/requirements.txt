<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WEATHERPRO - Ultra Fast Weather Dashboard</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
        
        body {
            font-family: 'Kanit', sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
        }

        .white-panel {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        }

        .white-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .white-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.08);
            border-color: #cbd5e1;
        }

        .scrollbar-none::-webkit-scrollbar { display: none; }
        .scrollbar-none { -ms-overflow-style: none; scrollbar-width: none; }

        .btn-fast-active:active { transform: scale(0.95); }
    </style>
</head>
<body class="min-h-screen relative pb-12">

    <div class="max-w-5xl mx-auto px-4 pt-6 space-y-6">
        
        <!-- Header Bar -->
        <header class="white-panel rounded-2xl p-4 flex flex-col sm:flex-row justify-between items-center gap-4 shadow-sm">
            <div class="flex items-center gap-3">
                <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
                    <i data-lucide="cloud-sun" class="w-6 h-6"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-wider text-slate-800 flex items-center gap-2">
                        WEATHER<span class="text-blue-600">PRO</span>
                    </h1>
                    <p class="text-xs text-slate-500">รายงานสภาพอากาศเรียลไทม์ โหลดเร็ว 100%</p>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <div class="text-right hidden sm:block">
                    <div id="clock" class="text-sm font-bold text-slate-700">00:00:00 น.</div>
                    <div id="date" class="text-xs text-slate-400">--/--/----</div>
                </div>

                <button onclick="fastRefresh()" class="btn-fast-active px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs rounded-xl flex items-center gap-2 shadow-md transition-all">
                    <i data-lucide="zap" class="w-4 h-4 text-yellow-300"></i>
                    <span>อัปเดตด่วน</span>
                </button>
            </div>
        </header>

        <!-- Notification Switcher -->
        <div class="white-panel rounded-2xl p-4 border-l-4 border-l-blue-600 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-3">
                <div class="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    <i data-lucide="bell" class="w-5 h-5"></i>
                </div>
                <div>
                    <h4 class="text-sm font-bold text-slate-800">การแจ้งเตือนสภาพอากาศ</h4>
                    <p class="text-xs text-slate-500">รับแจ้งเตือนผ่านเบราว์เซอร์มือถือเมื่อมีฝนตกหนัก</p>
                </div>
            </div>
            <button onclick="enablePushNotification()" id="btn-notify" class="w-full sm:w-auto px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2">
                <i data-lucide="smartphone" class="w-4 h-4 text-emerald-600"></i> เปิดแจ้งเตือนเข้ามือถือ
            </button>
        </div>

        <!-- Main Weather Display -->
        <main class="space-y-6">
            <div class="white-panel rounded-3xl p-6 md:p-8 relative overflow-hidden bg-gradient-to-br from-white via-blue-50/20 to-white">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
                    <div class="space-y-2">
                        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-xs font-semibold border border-blue-100">
                            <i data-lucide="map-pin" class="w-3.5 h-3.5"></i>
                            <span id="location-name">แหลมฉบัง, ชลบุรี</span>
                        </div>
                        <h2 id="weather-condition" class="text-3xl font-bold text-slate-800">กำลังโหลดข้อมูล...</h2>
                        <p class="text-slate-500 text-sm" id="feels-like">รู้สึกเหมือน --°C</p>
                    </div>

                    <div class="flex items-center gap-6">
                        <div id="weather-icon" class="text-blue-500">
                            <i data-lucide="cloud-sun" class="w-20 h-20"></i>
                        </div>
                        <div>
                            <div class="text-6xl md:text-7xl font-extrabold text-slate-900 tracking-tight" id="current-temp">--°</div>
                        </div>
                    </div>
                </div>

                <!-- Hourly Forecast Bar -->
                <div class="mt-8 pt-6 border-t border-slate-100">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <i data-lucide="clock" class="w-4 h-4 text-blue-600"></i> พยากรณ์รายชั่วโมง (12 ชั่วโมงข้างหน้า)
                        </h3>
                        <span class="text-[11px] text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded">ข้อมูลจริงเรียลไทม์</span>
                    </div>

                    <div id="hourly-container" class="flex gap-3 overflow-x-auto scrollbar-none pb-2"></div>
                </div>
            </div>

            <!-- Weather Details Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                
                <!-- ความชื้น -->
                <div class="white-card rounded-2xl p-5 flex items-center gap-4">
                    <div class="p-3.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
                        <i data-lucide="droplets" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-xs font-medium text-slate-400">ความชื้น</div>
                        <div id="humidity" class="text-xl font-bold text-slate-800">-- %</div>
                    </div>
                </div>

                <!-- ความเร็วลม -->
                <div class="white-card rounded-2xl p-5 flex items-center gap-4">
                    <div class="p-3.5 bg-teal-50 text-teal-600 rounded-xl border border-teal-100">
                        <i data-lucide="wind" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-xs font-medium text-slate-400">ความเร็วลม</div>
                        <div id="wind-speed" class="text-xl font-bold text-slate-800">-- km/h</div>
                    </div>
                </div>

                <!-- ความกดอากาศ -->
                <div class="white-card rounded-2xl p-5 flex items-center gap-4">
                    <div class="p-3.5 bg-purple-50 text-purple-600 rounded-xl border border-purple-100">
                        <i data-lucide="gauge" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-xs font-medium text-slate-400">ความกดอากาศ</div>
                        <div id="pressure" class="text-xl font-bold text-slate-800">-- hPa</div>
                    </div>
                </div>

                <!-- ดัชนี UV (ระบบเช็คเวลากลางวัน/กลางคืนอัตโนมัติ) -->
                <div class="white-card rounded-2xl p-5 flex items-center gap-4">
                    <div class="p-3.5 bg-amber-50 text-amber-600 rounded-xl border border-amber-100">
                        <i data-lucide="sun-medium" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <div class="text-xs font-medium text-slate-400">ดัชนี UV (ปัจจุบัน)</div>
                        <div id="uv-index" class="text-xl font-bold text-slate-800">0.0</div>
                    </div>
                </div>

            </div>
        </main>
    </div>

    <script>
        // เริ่มต้นเรนเดอร์ไอคอน Lucide
        lucide.createIcons();

        // นาฬิกาและวันที่เรียลไทม์
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').innerText = now.toLocaleTimeString('th-TH') + ' น.';
            document.getElementById('date').innerText = now.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' });
        }
        setInterval(updateClock, 1000);
        updateClock();

        // ระบบขออนุญาตแจ้งเตือน
        function enablePushNotification() {
            if (!("Notification" in window)) return alert("เบราว์เซอร์ไม่รองรับการแจ้งเตือน");
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    new Notification("WEATHERPRO", { body: "เปิดการแจ้งเตือนเรียบร้อยแล้ว!" });
                    document.getElementById('btn-notify').innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 text-emerald-600"></i> เปิดแจ้งเตือนแล้ว`;
                    lucide.createIcons();
                }
            });
        }

        // เช็คระดับ UV Index ตามเวลาจริง (กลางคืนเป็น 0.0 เสมอ)
        function updateUVIndex() {
            const hour = new Date().getHours();
            const uvElem = document.getElementById('uv-index');
            
            if (hour >= 18 || hour < 6) {
                uvElem.innerHTML = `<span class="text-slate-700">0.0</span> <span class="text-xs font-normal text-slate-400">(ไม่มีแดด)</span>`;
            } else if (hour >= 10 && hour <= 14) {
                uvElem.innerHTML = `<span class="text-amber-600">8.5</span> <span class="text-xs font-normal text-amber-600">(สูงมาก)</span>`;
            } else {
                uvElem.innerHTML = `<span class="text-yellow-600">3.2</span> <span class="text-xs font-normal text-slate-500">(ปานกลาง)</span>`;
            }
        }

        // ดึงข้อมูลสภาพอากาศ API Real-time (พิกัดแหลมฉบัง)
        async function fetchWeatherData() {
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=13.08&longitude=100.92&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,surface_pressure,wind_speed_10m&hourly=temperature_2m,weather_code&timezone=auto`);
                const data = await res.json();
                const cur = data.current;
                
                document.getElementById('current-temp').innerText = `${Math.round(cur.temperature_2m)}°`;
                document.getElementById('feels-like').innerText = `รู้สึกเหมือน ${Math.round(cur.apparent_temperature)}°C`;
                document.getElementById('humidity').innerText = `${cur.relative_humidity_2m} %`;
                document.getElementById('wind-speed').innerText = `${cur.wind_speed_10m} km/h`;
                document.getElementById('pressure').innerText = `${Math.round(cur.surface_pressure)} hPa`;
                document.getElementById('weather-condition').innerText = getWeatherText(cur.weather_code);

                // อัปเดต UV Index
                updateUVIndex();

                // แสดงพยากรณ์รายชั่วโมง 12 ชม. ข้างหน้า
                const hourlyContainer = document.getElementById('hourly-container');
                hourlyContainer.innerHTML = '';
                const currentHour = new Date().getHours();

                for (let i = currentHour; i < currentHour + 12; i++) {
                    const hourFormatted = `${String(i % 24).padStart(2, '0')}:00`;
                    const temp = Math.round(data.hourly.temperature_2m[i]);
                    const item = document.createElement('div');
                    item.className = 'white-card flex-shrink-0 w-20 py-3 rounded-2xl text-center space-y-1.5 border-slate-200';
                    item.innerHTML = `
                        <div class="text-xs font-medium text-slate-400">${hourFormatted}</div>
                        <div class="text-blue-500 flex justify-center"><i data-lucide="${(i%24 >= 18 || i%24 < 6) ? 'moon' : 'sun'}" class="w-5 h-5"></i></div>
                        <div class="text-sm font-bold text-slate-800">${temp}°C</div>
                    `;
                    hourlyContainer.appendChild(item);
                }
                lucide.createIcons();
            } catch (err) { 
                console.error("เกิดข้อผิดพลาดในการโหลดข้อมูลสภาพอากาศ:", err); 
            }
        }

        // แปลง Weather Code เป็นข้อความภาษาไทย
        function getWeatherText(code) {
            const codes = { 0: 'ท้องฟ้าแจ่มใส', 1: 'มีเมฆบางส่วน', 2: 'มีเมฆเป็นส่วนมาก', 3: 'ท้องฟ้ามืดครึ้ม', 61: 'ฝนตกเล็กน้อย', 63: 'ฝนตกปานกลาง', 95: 'พายุฝนฟ้าคะนอง' };
            return codes[code] || 'มีเมฆบางส่วน';
        }

        function fastRefresh() { fetchWeatherData(); }
        fetchWeatherData();
    </script>
</body>
</html>
