#!/bin/bash
# Cursor MCP 一键配置脚本

echo "🎯 Cursor MCP 配置助手"
echo "================================"

# 获取当前目录的绝对路径
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_CONFIG_FILE="$HOME/.cursor/mcp.json"

echo "📁 当前项目目录: $CURRENT_DIR"
echo "📄 MCP 配置文件: $MCP_CONFIG_FILE"

# 确保 .cursor 目录存在
mkdir -p "$HOME/.cursor"

# 检查现有配置
if [ -f "$MCP_CONFIG_FILE" ]; then
    echo "⚠️  发现现有 MCP 配置文件"
    echo "是否要备份现有配置？(y/n)"
    read -r BACKUP_CHOICE
    if [ "$BACKUP_CHOICE" = "y" ] || [ "$BACKUP_CHOICE" = "Y" ]; then
        cp "$MCP_CONFIG_FILE" "$MCP_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        echo "✅ 配置已备份"
    fi
fi

# 创建新的 MCP 配置
cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "ai-video-master": {
      "command": "uv",
      "args": ["run", "python", "server_official.py"],
      "cwd": "$CURRENT_DIR/mcp_server",
      "env": {
        "PYTHONPATH": "$CURRENT_DIR"
      }
    }
  }
}
EOF

echo "✅ MCP 配置文件已创建"

# 验证配置
echo ""
echo "📋 当前 MCP 配置："
cat "$MCP_CONFIG_FILE"

echo ""
echo "🧪 测试 MCP 服务器..."

# 测试 mcp_server
if [ -d "$CURRENT_DIR/mcp_server" ]; then
    cd "$CURRENT_DIR/mcp_server"
    echo "🔍 检查 mcp_server 依赖..."
    if uv sync > /dev/null 2>&1; then
        echo "✅ mcp_server 依赖正常"
    else
        echo "❌ mcp_server 依赖安装失败"
        echo "请手动运行: cd mcp_server && uv sync"
    fi
    cd "$CURRENT_DIR"
else
    echo "❌ mcp_server 目录不存在"
fi

echo ""
echo "🎉 MCP 配置完成！"
echo ""
echo "📋 下一步操作："
echo "1. 重启 Cursor IDE"
echo "2. 打开 Cursor Settings → Tools & Integrations → MCP Tools"
echo "3. 验证 'ai-video-master' 服务器显示为已连接"
echo "4. 在 Cursor 中测试工具："
echo "   - 使用 Agent 模式（Ctrl+Shift+I）"
echo "   - 输入: 使用 reverse_text 工具反转 'Hello MCP'"
echo ""
echo "🛠️ 可用工具："
echo "   • reverse_text - 文本反转测试"
echo "   • video_to_slice - 视频智能切片"
echo "   • video_to_srt - 视频转字幕"
echo "   • srt_to_product - 生成产品视频"
echo "   • slice_to_label - 视频片段标签分析"
echo ""
echo "🔧 故障排除："
echo "   • 查看 Cursor 输出: View → Output → Cursor MCP"
echo "   • 手动测试: cd mcp_server && uv run python server_official.py" 