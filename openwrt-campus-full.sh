#!/bin/sh
# ============================================
# 校园网登录 + 防检测脚本 - OpenWRT 完整版
# 包含: Web登录 + TTL统一 + 基本防检测
# ============================================

# ========== 配置 ==========
# 请在 config.ini 或环境变量中设置账号密码
GATEWAY="192.168.10.6"
PORT="801"
ESSID="SUES"
APNAME="train_5_2F_11"

# UA伪装：填写你浏览器登录时的完整User-Agent
CUSTOM_UA="${DRCOM_UA:-Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36}"

# 从环境变量读取账号密码
USERNAME="${DRCOM_USERNAME}"
PASSWORD="${DRCOM_PASSWORD}"
# ========================

LOG_FILE="/tmp/campus_login.log"

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

setup_ttl() {
    log "设置TTL统一..."
    # nftables (OpenWRT 21.02+)
    if command -v nft >/dev/null 2>&1; then
        nft add table inet mangle 2>/dev/null
        nft add chain inet mangle postrouting { type filter hook postrouting priority mangle\; } 2>/dev/null
        nft add rule inet mangle postrouting ip ttl set 64 2>/dev/null
        nft add rule inet mangle postrouting ip6 hoplimit set 64 2>/dev/null
        log "TTL已设置(nftables)"
    else
        # iptables
        iptables -t mangle -A POSTROUTING -j TTL --ttl-set 64 2>/dev/null
        ip6tables -t mangle -A POSTROUTING -j HL --hl-set 64 2>/dev/null
        log "TTL已设置(iptables)"
    fi
}

get_local_ip() {
    ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}'
}

check_network() {
    ping -c 1 -W 3 www.baidu.com >/dev/null 2>&1
}

do_login() {
    IP=$(get_local_ip)
    MAC=$(cat /sys/class/net/wan/address 2>/dev/null | tr ':' '-' || echo "000000000000")

    log "IP: $IP, MAC: $MAC"

    LOGIN_URL="http://${GATEWAY}:${PORT}/eportal/portal/login"
    FULL_URL="${LOGIN_URL}?callback=dr1001&login_method=1&user_account=${USERNAME}&user_password=${PASSWORD}&wlan_user_ip=${IP}&wlan_user_ipv6=&wlan_user_mac=${MAC}&wlan_ac_ip=&wlan_ac_name=${APNAME}&jsVersion=4.X&v=2048&lang=zh"

    log "登录中..."
    RESULT=$(curl -s -A "$CUSTOM_UA" -H "Referer: http://${GATEWAY}/" --connect-timeout 10 "$FULL_URL")
    log "响应: $RESULT"

    echo "$RESULT" | grep -qE '"result":"1"|"result":1'
}

main() {
    log "========== 启动 =========="

    if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
        log "错误: 请设置环境变量 DRCOM_USERNAME 和 DRCOM_PASSWORD"
        exit 1
    fi

    if check_network; then
        log "网络已通"
        exit 0
    fi

    log "网络未通，开始认证..."

    # 设置TTL统一（防检测）
    setup_ttl

    # 等待IP
    for i in $(seq 1 30); do
        IP=$(get_local_ip)
        [ -n "$IP" ] && break
        sleep 1
    done

    # 登录重试
    for i in $(seq 1 3); do
        if do_login; then
            sleep 2
            if check_network; then
                log "登录成功!"
                exit 0
            fi
        fi
        sleep 2
    done

    log "登录失败"
    exit 1
}

main "$@"
