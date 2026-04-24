#!/bin/sh
# ============================================
# 校园网自动登录脚本 - OpenWRT 基础版
# 适用于 Dr.COM Web 认证
# ============================================

# ========== 配置 ==========
# 请在 config.ini 或环境变量中设置账号密码
GATEWAY="192.168.10.6"
PORT="801"
ESSID="SUES"
APNAME="train_5_2F_11"

# 从环境变量或配置文件读取账号密码
USERNAME="${DRCOM_USERNAME}"
PASSWORD="${DRCOM_PASSWORD}"
# ==============================

LOG_FILE="/tmp/campus_login.log"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_local_ip() {
    ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}'
}

get_local_mac() {
    cat /sys/class/net/wan/address 2>/dev/null | tr ':' '-' || echo "000000000000"
}

check_network() {
    ping -c 1 -W 3 www.baidu.com >/dev/null 2>&1
    return $?
}

do_login() {
    IP=$(get_local_ip)
    MAC=$(get_local_mac)

    log "本机IP: $IP, MAC: $MAC"

    LOGIN_URL="http://${GATEWAY}:${PORT}/eportal/portal/login"
    FULL_URL="${LOGIN_URL}?callback=dr1001&login_method=1&user_account=${USERNAME}&user_password=${PASSWORD}&wlan_user_ip=${IP}&wlan_user_ipv6=&wlan_user_mac=${MAC}&wlan_ac_ip=&wlan_ac_name=${APNAME}&jsVersion=4.X&v=2048&lang=zh"

    log "发送登录请求..."

    RESULT=$(curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
        -H "Referer: http://${GATEWAY}/" \
        --connect-timeout 10 \
        "$FULL_URL")

    log "响应: $RESULT"

    if echo "$RESULT" | grep -qE '"result":"1"|"result":1'; then
        log "登录成功!"
        return 0
    else
        log "登录失败"
        return 1
    fi
}

main() {
    log "========== 校园网登录脚本启动 =========="

    if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
        log "错误: 请设置环境变量 DRCOM_USERNAME 和 DRCOM_PASSWORD"
        exit 1
    fi

    if check_network; then
        log "网络已通，无需认证"
        exit 0
    fi

    log "网络未通，开始认证..."

    # 等待获取IP
    for i in $(seq 1 30); do
        IP=$(get_local_ip)
        if [ -n "$IP" ] && [ "$IP" != "169.254.x.x" ]; then
            break
        fi
        log "等待IP分配... ($i/30)"
        sleep 1
    done

    if [ -z "$IP" ]; then
        log "无法获取IP，退出"
        exit 1
    fi

    # 执行登录（最多重试3次）
    for i in $(seq 1 3); do
        if do_login; then
            sleep 2
            if check_network; then
                log "验证通过，网络已连通"
                exit 0
            fi
        fi
        log "第${i}次登录失败，重试..."
        sleep 2
    done

    log "所有重试失败"
    exit 1
}

main "$@"
