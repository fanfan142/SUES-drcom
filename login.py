import requests
import socket
import subprocess
import re
import time
import uuid
import os
import configparser

# ========== 配置 ==========
# 账号密码请填写在 config.ini 或环境变量中，不要写在代码里！
GATEWAY = "192.168.10.6"
PORT = 801
# ==========================

# 读取配置文件
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists("config.ini"):
        config.read("config.ini", encoding="utf-8")
        return config
    return None

config = load_config()

# 从配置文件或环境变量读取账号密码
USERNAME = os.environ.get("DRCOM_USERNAME") or (config.get("account", "username") if config else "")
PASSWORD = os.environ.get("DRCOM_PASSWORD") or (config.get("account", "password") if config else "")
ESSID = os.environ.get("DRCOM_ESSID") or (config.get("network", "essid") if config else "SUES")
APNAME = os.environ.get("DRCOM_APNAME") or (config.get("network", "apname") if config else "train_5_2F_11")


def get_local_ip():
    """获取本机在内网中的IP"""
    # 方法1: 通过socket连接网关获取（最可靠）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect((GATEWAY, 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("169.254."):
            return ip
    except:
        pass

    # 方法2: 解析ipconfig输出，优先找Wi-Fi
    try:
        result = subprocess.check_output("ipconfig", shell=True, text=True, encoding='gbk')
        blocks = result.split('\n\n')
        wifi_blocks = [b for b in blocks if 'Wi-Fi' in b or '无线' in b or 'WLAN' in b]
        search_blocks = wifi_blocks + [b for b in blocks if '以太网' in b or 'Ethernet' in b]

        for block in search_blocks:
            for line in block.split('\n'):
                if 'IPv4' in line or 'IP 地址' in line:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip = match.group(1)
                        if not ip.startswith("169.254."):
                            return ip
    except:
        pass
    return None


def get_local_mac():
    """获取本机MAC地址"""
    # 优先用getmac找Wi-Fi适配器
    try:
        result = subprocess.check_output("getmac /v /fo csv /nh", shell=True, text=True, encoding='gbk')
        for line in result.split('\n'):
            if 'Wi-Fi' in line or 'WLAN' in line or '无线' in line:
                match = re.search('([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line)
                if match:
                    mac = match.group().replace('-', ':').upper()
                    return mac
    except:
        pass

    # Fallback: 从uuid.getnode()获取
    mac_hex = ':'.join(f'{(uuid.getnode() >> i) & 0xff:02x}' for i in range(0, 48, 8)[::-1])
    return mac_hex.upper()


def check_network():
    """检测网络是否畅通"""
    try:
        socket.create_connection(("www.baidu.com", 80), timeout=3)
        return True
    except OSError:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False


def wait_for_ip(timeout=30):
    """等待获取有效的内网IP"""
    print("等待获取IP...")
    last_ip = None
    for i in range(timeout):
        ip = get_local_ip()
        if ip and not ip.startswith("169.254."):
            print(f"  已获取IP: {ip}")
            return ip
        if ip:
            last_ip = ip
        print(f"  第{i+1}秒: 等待IP分配... (当前: {ip})")
        time.sleep(1)

    if last_ip and not last_ip.startswith("169.254."):
        print(f"  超时，使用最后的IP: {last_ip}")
        return last_ip
    return None


def verify_login():
    """验证网络是否真的通了"""
    for _ in range(3):
        try:
            resp = requests.get("http://www.baidu.com", timeout=5, allow_redirects=False)
            if resp.status_code in (200, 301, 302):
                return True
        except:
            pass
        time.sleep(1)
    return False


def login(host_ip=None, host_mac=None):
    """执行登录"""
    if not host_ip:
        host_ip = get_local_ip()
    if not host_mac:
        host_mac = get_local_mac()

    if not host_ip:
        print("无法获取本机IP")
        return False
    if not host_mac:
        print("无法获取本机MAC")
        return False

    mac_dash = host_mac.replace(':', '-')
    print(f"本机IP: {host_ip}")
    print(f"本机MAC: {host_mac}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })

    # 1. 先访问认证首页建立会话
    print("\n[1] 建立会话...")
    try:
        resp = session.get(
            f"http://{GATEWAY}/a79.htm?cmd=login&mac={host_mac}&ip={host_ip}&essid={ESSID}&apname={APNAME}&apgroup=train-apgroup&url=http%3A%2F%2Fwww.msftconnecttest.com%2Fredirect",
            timeout=5
        )
        print(f"    状态: {resp.status_code}")
    except Exception as e:
        print(f"    异常: {e}")

    # 2. 发送登录请求
    print("\n[2] 发送登录请求...")
    timestamp = str(int(time.time() * 1000))

    login_urls = [
        (f"http://{GATEWAY}:{PORT}/eportal/portal/login"
         f"?callback=dr1001&login_method=1"
         f"&user_account={USERNAME}&user_password={PASSWORD}"
         f"&wlan_user_ip={host_ip}&wlan_user_ipv6="
         f"&wlan_user_mac={mac_dash}"
         f"&wlan_ac_ip=&wlan_ac_name={APNAME}"
         f"&jsVersion=4.X&v=2048&lang=zh", "portal/login dr1001"),
        (f"http://{GATEWAY}:{PORT}/eportal/?c=Portal&a=login"
         f"&callback=dr{timestamp}&login_method=1"
         f"&user_account={USERNAME}&user_password={PASSWORD}"
         f"&wlan_user_ip={host_ip}&wlan_user_mac={mac_dash}"
         f"&wlan_ac_ip=&wlan_ac_name={APNAME}"
         f"&jsVersion=3.0&_={timestamp}", "Portal GET 时间戳"),
    ]

    for url, desc in login_urls:
        print(f"\n  尝试: {desc}")
        try:
            resp = session.get(url, timeout=10)
            print(f"    状态: {resp.status_code}")
            print(f"    响应: {resp.text[:150]}")
            if '"result":"1"' in resp.text or '"result":1' in resp.text:
                print("    => 服务器返回成功")
                print("\n[3] 验证网络连通性...")
                if verify_login():
                    print("    => 网络已通，登录成功!")
                    return True
                else:
                    print("    => 服务器说成功，但网络仍不通")
        except Exception as e:
            print(f"    异常: {e}")

    return False


if __name__ == "__main__":
    print("=" * 40)
    print("SUES 校园网自动登录脚本")
    print("=" * 40)

    if not USERNAME or not PASSWORD:
        print("错误: 请先配置账号密码！")
        print("方法1: 创建 config.ini 文件")
        print("方法2: 设置环境变量 DRCOM_USERNAME 和 DRCOM_PASSWORD")
        exit(1)

    if check_network():
        print("网络已通，无需认证")
    else:
        print("网络未通，开始认证...\n")
        host_ip = wait_for_ip(timeout=30)
        host_mac = get_local_mac()

        if not host_ip or host_ip.startswith("169.254."):
            print("无法获取有效IP，请检查WiFi是否已连接")
        else:
            success = login(host_ip, host_mac)
            if not success:
                print("\n登录失败，请检查账号密码或网络环境")
