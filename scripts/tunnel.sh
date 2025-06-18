#!/bin/bash
# 启动SSH隧道

set -e

# 加载配置
if [ -f .env.ssh-tunnel ]; then
    source .env.ssh-tunnel
else
    echo "错误：找不到 .env.ssh-tunnel 配置文件"
    exit 1
fi

# 默认值
LOCAL_PORT=${LOCAL_PORT:-8000}
REMOTE_PORT=${REMOTE_PORT:-12345}
REMOTE_HOST=${REMOTE_HOST:-lyh.ai}
SSH_OPTIONS=${SSH_OPTIONS:-"-o ServerAliveInterval=60"}
LOG_FILE=${LOG_FILE:-ssh-tunnel.log}

echo "===== 启动SSH隧道 ====="
echo "本地端口: $LOCAL_PORT"
echo "远程主机: $REMOTE_HOST"
echo "远程端口: $REMOTE_PORT"

# 检查SSH连接
if ! ssh -q $REMOTE_HOST exit; then
    echo "错误：无法连接到 $REMOTE_HOST"
    echo "请确保已正确配置SSH密钥或能够通过密码连接"
    exit 1
fi

# 检查端口占用
if lsof -i:$LOCAL_PORT > /dev/null; then
    echo "警告: 本地端口 $LOCAL_PORT 已被占用，服务可能已在运行"
fi

# 创建隧道目录
mkdir -p logs

echo "启动SSH隧道，按Ctrl+C停止..."
ssh $SSH_OPTIONS -R $REMOTE_PORT:localhost:$LOCAL_PORT $REMOTE_HOST -N -v 2>&1 | tee logs/$LOG_FILE 