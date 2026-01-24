import os
import signal
import subprocess
import glob
import json
import time
import re
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# --- ⚙️ 系统默认配置 (出厂默认值) ---
CONFIG_FILE = "serial_config.json"
DEFAULT_FALLBACK_IP = "192.168.1.233/24"
DEFAULT_FALLBACK_GW = "192.168.1.1"
DHCP_WAIT_TIMEOUT = 60 

current_process = None
current_config = {}

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Armbian 工业网关管理</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #1a1a1a; text-align: center; margin-bottom: 20px; }
        h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; color: #007bff; }
        h3 { color: #555; font-size: 1.1em; margin-top: 25px; margin-bottom: 10px; border-left: 4px solid #007bff; padding-left: 10px; }
        label { display: block; margin-top: 15px; font-weight: 600; color: #444; }
        select, input { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        .btn { width: 100%; padding: 14px; margin-top: 25px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; color: white; transition: 0.3s; }
        .btn-start { background-color: #28a745; }
        .btn-start:hover { background-color: #218838; }
        .btn-stop { background-color: #dc3545; }
        .btn-stop:hover { background-color: #c82333; }
        .btn-save { background-color: #007bff; }
        .btn-save:hover { background-color: #0056b3; }
        .btn-sub { background-color: #6c757d; font-size: 0.9em; padding: 10px; margin-top: 15px;}
        .btn-sub:hover { background-color: #5a6268; }
        .status-box { margin-top: 20px; padding: 20px; border-radius: 8px; text-align: center; }
        .running { background-color: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; }
        .stopped { background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; }
        .tag { display: inline-block; padding: 2px 8px; background: rgba(0,0,0,0.1); border-radius: 4px; font-size: 0.9em; margin: 0 2px;}
        .refresh a { text-decoration: none; color: #666; font-size: 0.9rem; }
        .row { display: flex; gap: 10px; }
        .col { flex: 1; }
        .info-tip { font-size: 0.85em; color: #666; margin-top: 5px; }
        .section-box { border: 1px dashed #ccc; padding: 15px; border-radius: 8px; background: #fafafa; margin-top: 15px; }
    </style>
    <script>
        function toggleStaticIP(val) {
            document.getElementById('static-fields').style.display = (val === 'manual') ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <h1>🛠️ Armbian 工业网关</h1>
    <div class="refresh" style="text-align: right; margin-bottom: 10px;"><a href="/">🔄 刷新页面</a></div>

    <div class="card">
        <h2>🚀 串口透传服务</h2>
        {% if running %}
            <div class="status-box running">
                <h3 style="margin:0 0 10px 0;">✅ 服务正在运行</h3>
                <p>掉电自动恢复: 已启用</p>
                <div style="text-align: left; margin-top: 15px;">
                    <label>设备:</label> <span class="tag">{{ config.device }}</span><br>
                    <label>参数:</label> <span class="tag">{{ config.baud }} / {{ config.parity }}</span><br>
                    <label>监听地址:</label> <span class="tag"><strong>{{ ip }}:{{ config.port }}</strong></span>
                </div>
            </div>
            <form action="/stop" method="post">
                <button type="submit" class="btn btn-stop">⛔ 停止服务</button>
            </form>
        {% else %}
            <div class="status-box stopped">❌ 服务未运行</div>
            <form action="/start" method="post">
                <label>串口设备:</label>
                <select name="device">
                    {% for port in ports %}
                    <option value="{{ port }}" {% if last_config.device == port %}selected{% endif %}>{{ port }}</option>
                    {% else %}
                    <option disabled>未检测到设备</option>
                    {% endfor %}
                </select>

                <div class="row">
                    <div class="col">
                        <label>波特率:</label>
                        <input type="number" name="baud" list="baud_list" value="{{ last_config.baud or '9600' }}" placeholder="9600">
                        <datalist id="baud_list">
                            <option value="115200">115200 (OpenWrt)</option>
                            <option value="9600">9600 (默认)</option>
                            <option value="4800">4800</option>
                            <option value="19200">19200</option>
                            <option value="38400">38400</option>
                        </datalist>
                    </div>
                    <div class="col">
                        <label>校验位:</label>
                        <select name="parity">
                            <option value="8N1" {% if last_config.parity == '8N1' %}selected{% endif %}>8N1 (无)</option>
                            <option value="8E1" {% if last_config.parity == '8E1' %}selected{% endif %}>8E1 (偶)</option>
                            <option value="8O1" {% if last_config.parity == '8O1' %}selected{% endif %}>8O1 (奇)</option>
                        </select>
                    </div>
                </div>

                <label>TCP 端口:</label>
                <input type="number" name="port" value="{{ last_config.port or '5000' }}">

                <button type="submit" class="btn btn-start">⚡ 启动服务</button>
            </form>
        {% endif %}
    </div>

    <div class="card">
        <h2>🌐 网络 IP 设置</h2>
        
        <form action="/network" method="post" onsubmit="return confirm('⚠️ 警告：\\n\\n正在修改本机运行 IP！\\n一旦应用，网络可能会立刻中断。\\n请务必记住您设置的新 IP。');">
            <h3>1. 运行模式设置</h3>
            <label>当前 IP 获取模式:</label>
            <select name="method" onchange="toggleStaticIP(this.value)">
                <option value="auto" {% if net_info.method == 'auto' %}selected{% endif %}>自动获取 (DHCP) - 推荐</option>
                <option value="manual" {% if net_info.method == 'manual' %}selected{% endif %}>静态固定 IP (Static)</option>
            </select>
            <div class="info-tip">提示: 当前本机 IP 为 {{ ip }}</div>

            <div id="static-fields" style="display: {% if net_info.method == 'manual' %}block{% else %}none{% endif %}; border-left: 2px solid #ddd; padding-left: 10px; margin-top: 10px;">
                <label>固定 IP 地址 (需带掩码, 如/24):</label>
                <input type="text" name="ip_address" value="{{ net_info.ip_address }}" placeholder="192.168.0.200/24">
                
                <label>网关 (Gateway):</label>
                <input type="text" name="gateway" value="{{ net_info.gateway }}" placeholder="192.168.0.1">

                <label>DNS 服务器:</label>
                <input type="text" name="dns" value="{{ net_info.dns }}" placeholder="114.114.114.114">
            </div>
            
            <button type="submit" class="btn btn-save">💾 应用运行 IP 设置</button>
        </form>

        <form action="/save_fallback" method="post" style="margin-top: 40px;">
            <h3>2. 异常保底设置 (Fallback)</h3>
            <div class="section-box">
                <div class="info-tip">ℹ️ 仅当“自动获取 DHCP”超时失败（如没插网线或无路由器）时，系统才会临时使用此 IP。</div>
                <div class="row">
                    <div class="col">
                        <label>保底 IP 地址:</label>
                        <input type="text" name="fallback_ip" value="{{ fallback_config.ip }}" placeholder="192.168.1.233/24">
                    </div>
                    <div class="col">
                        <label>保底网关:</label>
                        <input type="text" name="fallback_gw" value="{{ fallback_config.gw }}" placeholder="192.168.1.1">
                    </div>
                </div>
                <button type="submit" class="btn btn-sub">⚙️ 更新保底配置</button>
            </div>
        </form>
    </div>
</body>
</html>
"""

# --- 辅助函数 ---
def get_serial_ports():
    return glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')

def get_ip():
    try:
        cmd = "hostname -I | cut -d' ' -f1"
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

def run_cmd(cmd):
    try: return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return ""

# --- 配置管理 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {}

def save_config(new_data):
    # 增量更新配置，不覆盖已有字段
    data = load_config()
    data.update(new_data)
    with open(CONFIG_FILE, 'w') as f: json.dump(data, f)

# --- 网络管理 ---
def get_network_info():
    con_name = run_cmd("nmcli -t -f NAME,DEVICE connection show --active | head -n1 | cut -d: -f1")
    if not con_name: 
        con_name = run_cmd("nmcli -t -f NAME,TYPE connection show | grep ethernet | head -n1 | cut -d: -f1")
        if not con_name: return {"method": "auto", "ip_address": "", "gateway": "", "dns": "", "connection_name": "Unknown"}

    details = run_cmd(f"nmcli connection show '{con_name}'")
    method = "manual" if "ipv4.method:                          manual" in details else "auto"
    
    current_ip = get_ip() + "/24" if get_ip() else ""
    cfg_ip = re.search(r'ipv4.addresses:\s+([0-9\./]+)', details)
    if cfg_ip: current_ip = cfg_ip.group(1)
    
    cfg_gw = re.search(r'ipv4.gateway:\s+([0-9\.]+)', details)
    gateway = cfg_gw.group(1) if cfg_gw else ""
    
    cfg_dns = re.search(r'ipv4.dns:\s+([0-9\.]+)', details)
    dns = cfg_dns.group(1) if cfg_dns else ""

    return {"connection_name": con_name, "method": method, "ip_address": current_ip, "gateway": gateway, "dns": dns}

def apply_network_settings(con_name, method, ip="", gw="", dns=""):
    if method == "auto":
        full_cmd = f"nmcli connection modify '{con_name}' ipv4.method auto ipv4.addresses '' ipv4.gateway '' ipv4.dns '' && nmcli connection up '{con_name}'"
    else:
        full_cmd = f"nmcli connection modify '{con_name}' ipv4.method manual ipv4.addresses {ip} ipv4.gateway {gw} ipv4.dns {dns} && nmcli connection up '{con_name}'"
    subprocess.Popen(full_cmd, shell=True)

# --- 🟢 智能网络看门狗 ---
def smart_network_boot():
    print(f"🔄 网络看门狗: 正在检查连接... (超时: {DHCP_WAIT_TIMEOUT}s)")
    
    # 1. 检查是否为静态模式，如果是则跳过
    net_info = get_network_info()
    if net_info['method'] == 'manual':
        print("✅ 静态 IP 模式，跳过保底逻辑。")
        return

    # 2. 等待 DHCP
    if net_info['connection_name'] != "Unknown":
        start_time = time.time()
        while time.time() - start_time < DHCP_WAIT_TIMEOUT:
            if get_ip() and not get_ip().startswith("169.254"):
                print(f"✅ DHCP 成功: {get_ip()}")
                return
            time.sleep(2)
            print(".", end="", flush=True)

    # 3. 读取用户配置的保底 IP
    cfg = load_config()
    fb_ip = cfg.get('fallback_ip', DEFAULT_FALLBACK_IP)
    fb_gw = cfg.get('fallback_gw', DEFAULT_FALLBACK_GW)

    print(f"\n⚠️ DHCP 失败! 启用用户定义的保底 IP: {fb_ip}")
    apply_network_settings(net_info['connection_name'], "manual", fb_ip, fb_gw, "114.114.114.114")

# --- 路由 ---
@app.route('/')
def index():
    global current_config, current_process
    is_running = (current_process and current_process.poll() is None)
    
    if not is_running and current_config.get('running'):
        current_config['running'] = False
        save_config({'running': False})

    saved = load_config()
    # 传递 fallback 配置给前端
    fallback_config = {
        "ip": saved.get("fallback_ip", DEFAULT_FALLBACK_IP),
        "gw": saved.get("fallback_gw", DEFAULT_FALLBACK_GW)
    }

    return render_template_string(HTML_TEMPLATE, 
                                  ports=get_serial_ports(), 
                                  running=is_running,
                                  config=current_config,
                                  last_config=saved,
                                  net_info=get_network_info(),
                                  fallback_config=fallback_config,
                                  ip=get_ip())

@app.route('/start', methods=['POST'])
def start():
    global current_config
    device = request.form.get('device')
    baud = request.form.get('baud') or "9600"
    parity = request.form.get('parity')
    port = request.form.get('port')

    # Run socat
    global current_process
    if current_process:
        try: os.kill(current_process.pid, signal.SIGTERM)
        except: pass
    os.system("killall socat 2>/dev/null")

    parity_params = "cs8,parenb=0,cstopb=0"
    if parity == "8E1": parity_params = "cs8,parenb=1,parodd=0,cstopb=0"
    elif parity == "8O1": parity_params = "cs8,parenb=1,parodd=1,cstopb=0"

    cmd = ["socat", f"TCP-LISTEN:{port},fork,reuseaddr,nodelay", f"FILE:{device},b{baud},{parity_params},raw,echo=0"]
    try:
        current_process = subprocess.Popen(cmd)
        current_config = {"running": True, "device": device, "baud": baud, "parity": parity, "port": port}
        save_config(current_config)
    except: pass
    
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop():
    global current_process, current_config
    if current_process:
        try: os.kill(current_process.pid, signal.SIGTERM)
        except: pass
        current_process = None
    
    save_config({'running': False})
    current_config['running'] = False
    return redirect(url_for('index'))

@app.route('/network', methods=['POST'])
def network_settings():
    con_name = request.form.get('connection_name') or get_network_info()['connection_name']
    method = request.form.get('method')
    
    if method == 'manual':
        apply_network_settings(con_name, "manual", request.form.get('ip_address'), request.form.get('gateway'), request.form.get('dns'))
    else:
        apply_network_settings(con_name, "auto")
    
    return "正在应用网络设置... IP 变更后请手动访问新地址。"

@app.route('/save_fallback', methods=['POST'])
def save_fallback():
    # 仅仅保存到 json，不立即应用网络
    new_ip = request.form.get('fallback_ip')
    new_gw = request.form.get('fallback_gw')
    
    if new_ip and new_gw:
        save_config({'fallback_ip': new_ip, 'fallback_gw': new_gw})
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 1. 开机看门狗
    smart_network_boot()
    
    # 2. 恢复串口
    cfg = load_config()
    if cfg.get('running') == True and os.path.exists(cfg.get('device', '')):
        # 简单重构 run_socat 调用
        start_req = type('obj', (object,), {'form': {'device':cfg['device'], 'baud':cfg.get('baud','9600'), 'parity':cfg.get('parity','8N1'), 'port':cfg['port']}})
        with app.test_request_context('/start', method='POST', data=cfg):
            start() # 复用 start 逻辑

    app.run(host='0.0.0.0', port=8080, debug=False)
