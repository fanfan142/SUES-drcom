# 上海工程技术大学 (SUES) Dr.COM 校园网自动登录

适用于 SUES 校园网的 Dr.COM Web 认证自动登录脚本。

## 环境信息

| 项目 | 值 |
|------|-----|
| 认证网关 | `192.168.10.6` |
| 认证端口 | `801` |
| ESSID | `SUES` |
| AP 名称 | `train_5_2F_11` |

## 重要：账号密码配置

**账号密码不要写在代码里！** 请选择以下方式之一：

### 方式1：配置文件（推荐）

```bash
cp config.ini.example config.ini
# 然后编辑 config.ini，填入你的账号密码
```

### 方式2：环境变量

```bash
export DRCOM_USERNAME="你的账号"
export DRCOM_PASSWORD="你的密码"
```

## 目录结构

```
sues-drcom/
├── README.md           # 说明文档
├── login.py           # Windows Python 脚本
├── openwrt-campus-login.sh   # OpenWRT 基础版
├── openwrt-campus-full.sh    # OpenWRT 完整版（带TTL）
├── config.ini.example  # 配置文件模板
├── requirements.txt    # Python 依赖
└── .gitignore         # Git忽略文件
```

## 使用方法

### Windows 电脑

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python login.py
```

### OpenWRT 路由器

```bash
# 上传脚本
scp login.py root@192.168.1.1:/etc/storage/
scp config.ini root@192.168.1.1:/etc/storage/
scp openwrt-campus-full.sh root@192.168.1.1:/etc/storage/

# SSH进路由器
ssh root@192.168.1.1

# 赋予执行权限
chmod +x /etc/storage/openwrt-campus-full.sh

# 设置定时任务（每5分钟检测）
echo "*/5 * * * * /etc/storage/openwrt-campus-full.sh" >> /etc/crontabs/root

# 重启cron
/etc/init.d/cron enable
/etc/init.d/cron restart
```

## 防检测说明

如果校园网检测多设备，需要：

1. **MAC 克隆**：OpenWRT WAN 口 MAC 设为电脑的 MAC
2. **TTL 统一**：脚本中已包含防火墙规则
3. **UA 伪装**：使用 UA-Mask 插件

详见：[校园网破解方案](https://blog.neolnax.top/posts/校园网破解/)

## License

MIT
