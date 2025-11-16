# 🚀 AI Video Master MCP 快速启动指南

## 📁 项目结构说明

我们已经将MCP相关文件组织到专门的 `mcp_server/` 目录下，这样可以保持项目结构清晰：

```
demo/                        # 项目根目录
├── mcp_server/             # 🎯 MCP服务器目录
│   ├── mcp_server.py       # MCP服务器主文件
│   ├── setup_mcp.sh        # 安装配置脚本
│   ├── pyproject.toml      # Python项目配置
│   └── MCP_README.md       # 详细文档
├── video_to_slice/         # 视频切片模块
├── video_to_srt/          # 视频转字幕模块
├── srt_to_product/        # 产品视频模块
└── slice_to_label/        # 标签分析模块
```

## ⚡ 3分钟快速安装

### 步骤1: 进入MCP服务器目录
```bash
cd mcp_server
```

### 步骤2: 运行安装脚本
```bash
# 给脚本执行权限
chmod +x setup_mcp.sh

# 运行安装脚本（自动完成所有配置）
./setup_mcp.sh
```

安装脚本会自动：
- ✅ 检查Python环境 (需要3.10+)
- ✅ 安装UV包管理器  
- ✅ 创建MCP虚拟环境
- ✅ 安装MCP依赖
- ✅ 检查各模块状态
- ✅ 创建配置文件

### 步骤3: 配置API密钥
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件，填入你的API密钥
nano .env
```

**必需配置：**
```bash
# Google Cloud Video Intelligence API
GOOGLE_APPLICATION_CREDENTIALS=../video_to_slice/config/your-service-account.json

# DashScope API (阿里云)
DASHSCOPE_API_KEY=your_dashscope_api_key

# DeepSeek API  
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 步骤4: 启动测试
```bash
# 测试MCP服务器
./test_mcp_server.py

# 启动MCP服务器
./start_mcp_server.sh
```

## 🔗 客户端配置

### Claude Desktop 配置

1. 打开配置文件：
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. 添加配置（使用绝对路径）：
```json
{
  "mcpServers": {
    "ai-video-master": {
      "command": "/Users/sshlijy/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/sshlijy/Desktop/demo/mcp_server",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

3. 重启Claude Desktop

### Cursor 配置

使用生成的 `mcp_config.json` 文件：
```json
{
  "mcpServers": {
    "ai-video-master": {
      "command": "python",
      "args": ["/Users/sshlijy/Desktop/demo/mcp_server/mcp_server.py"],
      "env": {
        "PATH": "/Users/sshlijy/Desktop/demo/mcp_server/.venv/bin:$PATH"
      }
    }
  }
}
```

## 🛠️ 可用工具

| 工具 | 功能 | 示例使用 |
|------|------|----------|
| `video_to_slice` | 视频智能切片 | 将长视频分割成语义片段 |
| `video_to_srt` | 视频转字幕 | 生成高精度SRT字幕文件 |
| `srt_to_product` | 产品视频生成 | 从字幕中提取产品介绍片段 |
| `slice_to_label` | 片段标签分析 | 为视频片段添加智能标签 |

## 💡 使用提示

1. **目录路径**: 所有路径都是相对于各模块的工作目录
2. **API配额**: Google Cloud有API调用限制，建议合理控制并发数
3. **文件格式**: 支持常见视频格式 (.mp4, .mov, .avi, .mkv等)
4. **专业优化**: 内置婴幼儿奶粉领域专业词汇优化

## 🐛 常见问题

- **Python版本**: 需要Python 3.10+
- **API密钥**: 确保所有必需的API密钥都已正确配置
- **模块环境**: 确保各个模块的虚拟环境已正确设置
- **路径问题**: MCP服务器从 `mcp_server/` 目录访问上级目录的模块

## 📚 更多信息

详细文档请查看 [`mcp_server/MCP_README.md`](mcp_server/MCP_README.md) 

## 🚀 快速部署（5分钟设置）

### 步骤1: 验证环境
```bash
# 确认在项目根目录
cd /Users/sshlijy/Desktop/demo

# 检查UV是否安装
which uv
# 应该显示: /Users/sshlijy/.local/bin/uv

# 检查Claude Desktop是否安装
ls -la "/Applications/Claude.app"
```

### 步骤2: 安装MCP服务器
```bash
cd mcp_server
source setup_mcp.sh
```

### 步骤3: 测试服务器
```bash
# 运行测试脚本
/Users/sshlijy/.local/bin/uv run test_server.py

# 应该看到所有✅绿色检查标记
```

### 步骤4: 配置Claude Desktop

配置文件已自动创建在正确位置：
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

应该显示：
```json
{
  "mcpServers": {
    "ai-video-master": {
      "command": "/Users/sshlijy/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/sshlijy/Desktop/demo/mcp_server",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

### 步骤5: 重启Claude Desktop

1. 完全退出Claude Desktop应用
2. 重新启动Claude Desktop
3. 等待应用完全加载

### 步骤6: 验证部署

在Claude Desktop中检查：

1. **查看工具图标**: 聊天界面左下角应该出现🔨工具图标
2. **点击工具图标**: 应该看到4个可用工具：
   - video_to_slice
   - video_to_srt  
   - srt_to_product
   - slice_to_label

3. **测试连接**: 在聊天中输入：
   ```
   列出所有可用的视频处理工具
   ```

## 🔧 详细配置

### API密钥配置

根据使用的工具配置相应的API密钥：

#### Google Cloud (video_to_slice)
```bash
# 在 video_to_slice/config/ 目录下配置
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

#### DashScope (video_to_srt)
```bash
# 编辑 video_to_srt/config/env_config.txt
echo "DASHSCOPE_API_KEY=your_key_here" > video_to_srt/config/env_config.txt
```

#### DeepSeek (srt_to_product)
```bash
# 编辑 srt_to_product/config/env_config.txt  
echo "DEEPSEEK_API_KEY=your_key_here" > srt_to_product/config/env_config.txt
```

### 高级配置选项

#### 修改并发设置
```python
# 在Claude中使用时可以指定参数
video_to_slice(
    input_dir="/path/to/videos",
    concurrent=2,        # 降低并发数
    ffmpeg_workers=6     # 增加FFmpeg线程
)
```

#### 自定义输出路径
```python
# 所有工具都支持自定义输出路径
video_to_srt(
    input_dir="/path/to/videos",
    output_dir="/custom/output/path"
)
```

## 📖 使用指南

### 基本使用示例

#### 1. 视频智能切片
```
请使用video_to_slice工具处理/Users/sshlijy/Desktop/demo/video_to_slice/data/input目录下的视频文件
```

#### 2. 视频转字幕
```
请将/Users/sshlijy/Desktop/demo/video_to_srt/data/input目录下的视频转换为SRT字幕文件
```

#### 3. 字幕转产品视频
```
请基于/Users/sshlijy/Desktop/demo/video_to_srt/data/output目录的字幕文件生成产品介绍视频片段
```

#### 4. 视频片段标签分析
```
请分析/Users/sshlijy/Desktop/demo/slice_to_label/data/input/4目录下视频片段的标签
```

### 工作流组合示例

#### 完整处理流程
```
请按以下步骤处理视频：
1. 首先用video_to_slice切片
2. 然后用slice_to_label分析标签
3. 最后生成分析报告
```

#### 字幕处理流程
```
请帮我：
1. 将视频转换为字幕
2. 基于字幕提取产品介绍片段
3. 总结产品要点
```

## 🛠️ 故障排除

### 常见问题和解决方案

#### 问题1: 服务器连接失败
**症状**: Claude Desktop显示"failed"状态

**解决方案**:
```bash
# 1. 检查配置文件
python3 -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 2. 测试服务器启动
cd /Users/sshlijy/Desktop/demo/mcp_server
/Users/sshlijy/.local/bin/uv run mcp_server.py

# 3. 检查日志
tail -f ~/Library/Logs/Claude/mcp*.log
```

#### 问题2: 工具不显示
**症状**: 看不到🔨工具图标

**解决方案**:
1. 确保完全重启Claude Desktop
2. 检查配置文件路径是否正确
3. 验证JSON格式是否有效

#### 问题3: 工具执行失败
**症状**: 工具调用返回错误

**解决方案**:
```bash
# 检查API密钥
ls -la video_to_slice/config/
ls -la video_to_srt/config/env_config.txt
ls -la srt_to_product/config/env_config.txt

# 检查输入路径
ls -la /path/to/your/input/directory
```

### 调试命令

#### 查看详细日志
```bash
# Claude Desktop日志
tail -f ~/Library/Logs/Claude/mcp.log
tail -f ~/Library/Logs/Claude/mcp-server-ai-video-master.log

# 手动启动服务器（调试模式）
cd /Users/sshlijy/Desktop/demo/mcp_server
export MCP_DEBUG=1
/Users/sshlijy/.local/bin/uv run mcp_server.py
```

#### 测试单个模块
```bash
# 测试video_to_slice模块
cd video_to_slice
source activate_envs.sh video_to_slice
python src/parallel_batch_processor.py --help

# 测试video_to_srt模块  
cd video_to_srt
source activate_envs.sh video_to_srt
python src/batch_video_to_srt.py --help
```

### 性能优化建议

#### 1. 系统资源优化
- **内存**: 建议至少8GB RAM
- **存储**: 确保有足够SSD空间
- **网络**: 稳定的网络连接（API调用）

#### 2. 并发控制
```python
# 根据系统性能调整
video_to_slice(
    input_dir="/path/to/videos",
    concurrent=2,        # 系统较慢时减少并发
    ffmpeg_workers=4     # 根据CPU核心数调整
)
```

#### 3. 批处理建议
- 小批量测试：先用1-2个文件测试
- 分批处理：大量文件分多次处理
- 监控资源：注意CPU、内存、磁盘使用

## 📚 进阶使用

### 自定义工作流

#### 情绪分析工作流
```
请帮我分析视频中的情绪变化：
1. 先切片视频
2. 分析每个片段的情绪标签
3. 生成情绪变化报告
```

#### 产品营销工作流  
```
请帮我制作产品营销素材：
1. 提取视频字幕
2. 识别产品介绍片段
3. 分析片段情绪和标签
4. 推荐最佳营销片段
```

### API配额管理

#### 监控使用量
- Google Cloud: 查看Cloud Console配额页面
- DashScope: 查看阿里云控制台
- DeepSeek: 查看API使用统计

#### 优化策略
- 使用缓存减少重复调用
- 合理设置并发数
- 分时段处理避开高峰

## 🔄 更新和维护

### 更新MCP服务器
```bash
cd /Users/sshlijy/Desktop/demo/mcp_server
git pull origin main
source setup_mcp.sh
```

### 清理临时文件
```bash
# 清理各模块的临时文件
find . -name "temp" -type d -exec rm -rf {} +
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### 备份配置
```bash
# 备份Claude Desktop配置
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json ~/Desktop/claude_config_backup.json

# 备份API密钥配置
tar -czf ~/Desktop/api_configs_backup.tar.gz */config/env_config.txt
```

## 📞 支持

### 获取帮助
1. 查看详细文档：`mcp_server/MCP_README.md`
2. 运行测试脚本：`uv run test_server.py`
3. 查看日志文件：`~/Library/Logs/Claude/mcp*.log`
4. 检查各模块README文件

### 报告问题
提供以下信息：
- 错误日志
- 配置文件内容  
- 系统环境信息
- 复现步骤

---

🎉 **恭喜！** 你现在可以通过Claude Desktop使用强大的AI视频处理工具了！

通过自然语言与Claude交互，享受智能视频处理的便利。 