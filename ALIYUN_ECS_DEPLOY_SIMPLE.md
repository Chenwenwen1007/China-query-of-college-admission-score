# 阿里云 ECS 最简单公网部署指南

这份方案适合当前项目直接给朋友公网访问，目标是：

- 不需要域名
- 不需要 Nginx
- 不需要 Docker
- 先用公网 IP + 端口跑起来

部署完成后，朋友可直接访问：

```text
http://你的服务器公网IP:8000/?province=hunan
```

也可以切换省份：

```text
http://你的服务器公网IP:8000/?province=guangdong
http://你的服务器公网IP:8000/?province=jiangxi
```

## 方案说明

当前项目是：

- Python HTTP 服务
- 前端静态页面
- 本地 SQLite 数据库

线上给朋友查询使用时，只需要运行查询服务，不需要在服务器上重新构建数据库。

也就是说，直接把下面这些内容上传到服务器即可：

- `frontend_server.py`
- `province_config.py`
- `frontend/`
- `configs/`
- 需要用到的 `.sqlite3` 数据库文件

推荐直接把整个项目目录上传，最省事。

## 一、阿里云控制台准备

先确认你的 ECS 满足这两点：

1. 已分配公网 IP
2. 安全组已放行 `8000` 端口

### 安全组放行示例

- 方向：入方向
- 协议类型：自定义 TCP
- 端口范围：`8000/8000`
- 授权对象：`0.0.0.0/0`

如果你后面想更正式一点，也可以改成开放 `80` 端口。

## 二、连接服务器

以下示例默认服务器系统为 Ubuntu。

先通过 SSH 登录：

```bash
ssh root@你的服务器公网IP
```

如果你不是 `root`，把下面命令中的路径按你的账号调整即可。

## 三、安装基础环境

更新系统并安装 Python：

```bash
apt update
apt install -y python3 python3-venv python3-pip
```

检查版本：

```bash
python3 --version
```

## 四、上传项目

推荐把本地整个项目目录上传到服务器，例如传到：

```text
/opt/China-query-of-college-admission-score
```

如果你本地是 Windows，可以在本地 PowerShell 里执行：

```powershell
scp -r F:\Pyhton_Project\China-query-of-college-admission-score root@你的服务器公网IP:/opt/
```

上传后，服务器上的项目路径应类似：

```text
/opt/China-query-of-college-admission-score
```

## 五、安装项目运行依赖

进入项目目录：

```bash
cd /opt/China-query-of-college-admission-score
```

创建虚拟环境：

```bash
python3 -m venv .venv
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

安装最小运行依赖：

```bash
pip install --upgrade pip
pip install openpyxl
```

说明：

- 查询服务运行只需要 `openpyxl`
- 如果你要在服务器上重新抓数据、重新构建数据库，再额外安装：

```bash
pip install pandas pdfplumber requests
```

## 六、先手动启动测试

先直接启动，确认程序没问题：

```bash
cd /opt/China-query-of-college-admission-score
source .venv/bin/activate
python3 frontend_server.py --province hunan --host 0.0.0.0 --port 8000
```

如果看到类似输出：

```text
Serving hunan default on http://0.0.0.0:8000
```

说明服务已经启动。

这时在你自己的电脑浏览器打开：

```text
http://你的服务器公网IP:8000/?province=hunan
```

如果能打开页面，说明公网访问已经通了。

按 `Ctrl+C` 可以停止这个前台测试进程。

## 七、设置为后台常驻运行

推荐用 `systemd`，这样服务器重启后也会自动启动。

先创建服务文件：

```bash
cat >/etc/systemd/system/admissions.service <<'EOF'
[Unit]
Description=China Query of College Admission Score
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/China-query-of-college-admission-score
ExecStart=/opt/China-query-of-college-admission-score/.venv/bin/python frontend_server.py --province hunan --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

重新加载配置并启动：

```bash
systemctl daemon-reload
systemctl enable admissions
systemctl start admissions
```

检查状态：

```bash
systemctl status admissions
```

查看日志：

```bash
journalctl -u admissions -f
```

## 八、访问地址

部署完成后可直接访问：

```text
http://你的服务器公网IP:8000/?province=hunan
```

其他省份：

```text
http://你的服务器公网IP:8000/?province=guangdong
http://你的服务器公网IP:8000/?province=jiangxi
```

## 九、后续更新项目

如果你在本地改了代码，需要重新上传服务器，然后重启服务：

```bash
systemctl restart admissions
```

如果只是替换数据库文件，也建议重启一次：

```bash
systemctl restart admissions
```

## 十、常见问题

### 1. 浏览器打不开

优先检查这几项：

- ECS 是否真的有公网 IP
- 安全组是否放行了 `8000`
- 服务器系统防火墙是否拦截了 `8000`
- 服务是否成功监听在 `0.0.0.0:8000`

可在服务器执行：

```bash
ss -ltnp | grep 8000
```

### 2. 能 SSH，但网页打不开

大概率是安全组或系统防火墙问题。

Ubuntu 如果启用了 `ufw`，可以执行：

```bash
ufw allow 8000/tcp
ufw status
```

### 3. 启动时报数据库不存在

说明数据库文件没有上传完整，或者路径不在项目根目录。

当前项目会从各省配置文件里读取数据库文件名，并默认在项目根目录找对应 `.sqlite3` 文件。

### 4. 可以访问，但想更正式一点

后续建议升级为：

- 域名
- Nginx
- HTTPS
- 80/443 标准端口

这样朋友访问会更方便，链接也更像正式网站。

## 十一、当前项目最省事的部署建议

对于当前仓库，最简单可行的做法就是：

1. 把整个项目目录上传到 ECS
2. 安装 `python3`、`python3-venv`
3. 用虚拟环境安装 `openpyxl`
4. 用 `python3 frontend_server.py --host 0.0.0.0 --port 8000` 启动
5. 放行阿里云安全组 `8000`
6. 用 `systemd` 常驻

这样就能先稳定给朋友用了。
