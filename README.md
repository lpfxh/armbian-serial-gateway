<div align="center">

# 🔌 Armbian Web Serial Gateway
### 工业级串口透传网关 (Industrial Serial Server)

<p>
  <img src="https://img.shields.io/badge/Platform-Armbian%20%7C%20Linux-orange?style=flat-square&logo=linux" alt="Platform">
  <img src="https://img.shields.io/badge/Language-Python%203-blue?style=flat-square&logo=python" alt="Language">
  <img src="https://img.shields.io/badge/Backend-Flask-green?style=flat-square&logo=flask" alt="Backend">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License">
</p>

<p>
  <b>无需 SSH，将普通的 Armbian 盒子瞬间变身为专业的工业串口服务器。</b><br>
  <i>支持 Web 可视化管理、掉电记忆、智能网络保底。</i>
</p>

</div>

---

## ✨ 核心功能 (Features)

### 🌐 可视化管理
- **Web 界面**：抛弃繁琐的命令行，通过浏览器直接配置串口参数。
- **状态监控**：实时查看服务运行状态、当前端口及参数。

### 🛠️ 工业级参数支持
- **全波特率覆盖**：支持标准波特率及自定义输入 (如 `1200` ~ `1500000` bps)。
- **校验位支持**：完美支持 `8N1`、`8E1` (偶校验)、`8O1` (奇校验)，兼容 PLC 与工业仪表。
- **掉电记忆**：自动保存最后一次配置，断电重启后自动恢复工作，无需人工干预。

### 🛡️ 智能网络看门狗 (Smart Watchdog)
> 专为无头模式 (Headless) 设计，防止设备 IP 变动导致失联。
- **自动保底机制**：开机 `60秒` 内若 DHCP 未获取到 IP，系统自动切换至 **保底静态 IP**。
- **默认保底 IP**：`192.168.1.233` (可通过 Web 界面修改)。

### 🔌 纯净透传模式
- **数据零篡改**：采用 `socat` 的 `raw,echo=0` 模式，确保二进制数据原样传输。
- **低延迟优化**：支持 TCP `Nodelay`，完美兼容 **HW VSP3** (Windows 虚拟串口) 及 **Putty**。

---

## 🚀 快速部署 (Quick Start)

### 1. 安装依赖
```bash
sudo apt update
sudo apt install socat git python3-pip -y
pip3 install flask
