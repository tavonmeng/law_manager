#!/bin/bash
# 阿里云/Linux 一键部署脚本

echo ">>> 开始部署基于前后端分离的合规排查系统至服务器..."

# 检查权限
if [ "$EUID" -ne 0 ]; then
  echo "请使用 root 权限运行此脚本 (sudo ./deploy_aliyun.sh)"
  exit
fi

# 检查并安装 docker 
if ! command -v docker &> /dev/null
then
    echo "未检测到 Docker，正在尝试通过阿里云镜像自动安装..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl enable docker
    systemctl start docker
fi

# 检查并安装 docker-compose
if ! command -v docker-compose &> /dev/null
then
    echo "未检测到 docker-compose，正在尝试安装..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo ">> 正在通过 docker-compose 构建并启动服务 (后台运行)..."
docker-compose down
docker-compose build
docker-compose up -d

echo ""
echo "✅ 恭喜！部署已完成！"
echo "前端体验地址: http://<你的服务器公网IP>:8501"
echo "后端 API 地址: http://<你的服务器公网IP>:8000/docs (Swagger 接口文档)"
echo ""
echo "❗注意事项："
echo "1. 请务必在阿里云 ECS 控制台的【安全组】规则中，添加入方向放行 8000 和 8501 端口。"
echo "2. 如果前端无法连接后端，请在打开的前端页面左侧设置好您服务器公网 IP 的正确 API 地址。"
