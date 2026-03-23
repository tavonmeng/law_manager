#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 阿里云 ECS 一键部署脚本
# 合规尽调 Agent 评测平台
# ═══════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  合规尽调 Agent 评测平台 · 阿里云部署"
echo "═══════════════════════════════════════════════════════════"

# ── 检查权限 ──────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  echo "❌ 请使用 root 权限: sudo ./deploy_aliyun.sh"
  exit 1
fi

# ── 自动检测服务器公网 IP ─────────────────────────────────────
PUBLIC_IP=$(curl -s --connect-timeout 5 http://ifconfig.me || curl -s --connect-timeout 5 http://ipinfo.io/ip || echo "YOUR_SERVER_IP")
echo "📡 检测到公网 IP: $PUBLIC_IP"

# ── 安装 Docker ──────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo "🔧 安装 Docker（阿里云镜像）..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker 安装完成"
fi

# ── 安装 Docker Compose ──────────────────────────────────────
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "🔧 安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 安装完成"
fi

# ── 判断使用 docker-compose 还是 docker compose ──────────────
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    DC="docker compose"
fi

# ── 构建并启动 ───────────────────────────────────────────────
echo "🏗️  构建 Docker 镜像（首次较慢，请耐心等待）..."
$DC down 2>/dev/null || true
$DC build
$DC up -d

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ 部署完成！"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  📊 前端地址: http://$PUBLIC_IP:8501"
echo "  🔌 后端 API: http://$PUBLIC_IP:8000/docs"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ⚠️  必要操作（否则外网无法访问）:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  1. 登录阿里云 ECS 控制台"
echo "  2. 找到实例 → 安全组 → 配置规则"
echo "  3. 添加入方向规则:"
echo "     端口: 8000/8000  协议: TCP  授权对象: 0.0.0.0/0"
echo "     端口: 8501/8501  协议: TCP  授权对象: 0.0.0.0/0"
echo ""
echo "  4. 打开前端页面后，在左侧边栏将后端地址改为:"
echo "     http://$PUBLIC_IP:8000"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  常用运维命令:"
echo "  查看日志:  $DC logs -f"
echo "  重启服务:  $DC restart"
echo "  停止服务:  $DC down"
echo "  重新构建:  $DC build && $DC up -d"
echo "═══════════════════════════════════════════════════════════"
