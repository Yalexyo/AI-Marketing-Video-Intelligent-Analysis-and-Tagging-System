# Script Digest 系统架构文档

## 📋 清理后的项目结构

```
Script_Digest/
├── 📄 主程序文件
│   ├── run.py              # 🚀 主入口程序 (ScriptDigestMain)
│   ├── start.sh           # 🎬 启动脚本 (可执行)
│   ├── README.md          # 📖 用户使用说明
│   └── pyproject.toml     # 📦 项目配置文件
│
├── 📂 src/ - 核心源代码模块
│   ├── script_parser.py     # 🔍 脚本解析器
│   ├── json_analyzer.py     # 📊 JSON分析器  
│   ├── video_matcher.py     # 🎯 视频匹配器
│   ├── file_organizer.py    # 📂 文件组织器
│   ├── deepseek_client.py   # 🤖 DeepSeek AI客户端
│   └── env_loader.py        # 🔧 环境变量加载器
│
├── 📂 config/ - 配置管理
│   ├── dynamic_match_config.py  # ⚙️ 动态匹配配置
│   └── env_config.example.txt   # 📋 环境配置模板
│
├── 📂 data/ - 数据目录
│   ├── input/               # 📥 输入数据目录
│   └── output/              # 📤 输出结果目录
│
├── 📂 logs/ - 日志文件
│   └── script_digest.log    # 📝 系统运行日志
│
├── 📂 cache/ - 缓存目录
│   └── (运行时生成)          # 💾 临时缓存文件
│
└── 📂 🍭Origin/ - 原始数据
    └── (可选)                # 📄 原始脚本或素材
```

## 🔗 核心模块依赖关系

### 主程序 (run.py)
- **职责**: 系统入口、流程控制、用户交互
- **依赖**: 所有其他模块
- **功能**: 
  - 提供默认脚本选择
  - 管理完整的处理流程
  - 用户友好的交互界面

### 脚本解析器 (script_parser.py)
- **职责**: 解析用户输入的脚本段落
- **依赖**: dynamic_match_config.py
- **输入**: Dict[str, str] (segment_id: content)
- **输出**: 结构化的脚本分析结果

### JSON分析器 (json_analyzer.py)  
- **职责**: 扫描和解析视频切片的JSON文件
- **依赖**: 无直接依赖
- **输入**: 视频切片目录路径
- **输出**: 视频特征数据列表

### 视频匹配器 (video_matcher.py)
- **职责**: 核心匹配逻辑，协调AI分析
- **依赖**: deepseek_client.py, script_parser.py, json_analyzer.py
- **功能**: 语义匹配、分数计算、结果筛选

### DeepSeek客户端 (deepseek_client.py)
- **职责**: AI API调用封装
- **依赖**: env_loader.py
- **功能**: HTTP请求、JSON解析、错误处理

### 文件组织器 (file_organizer.py)
- **职责**: 智能文件夹命名和文件组织
- **依赖**: video_matcher.py的输出
- **功能**: 
  - emoji数字解析 (1️⃣ → 1)
  - 文件夹命名 (【序号+内容...】)
  - 文件复制/链接

### 环境加载器 (env_loader.py)
- **职责**: 智能配置文件复用
- **依赖**: 无直接依赖
- **功能**: 
  - 多项目配置复用
  - API密钥管理
  - 配置文件智能查找

### 动态配置管理器 (dynamic_match_config.py)
- **职责**: 匹配规则和提示模板管理
- **依赖**: 无直接依赖
- **功能**:
  - 关键词映射表
  - AI提示模板
  - 段落类型分析

## 🚀 系统工作流程

```
1. 用户启动 (start.sh / run.py)
   ↓
2. 脚本输入选择 (默认脚本 / 自定义)
   ↓
3. 脚本解析 (script_parser + dynamic_match_config)
   ↓
4. 视频目录选择 & JSON文件扫描 (json_analyzer)
   ↓
5. AI语义匹配 (video_matcher + deepseek_client)
   ↓
6. 文件组织 (file_organizer)
   ↓
7. 结果展示 (主程序)
```

## 📦 关键特性

### 🎯 智能匹配
- 基于DeepSeek AI的语义分析
- 动态配置的匹配规则
- 多维度特征匹配 (对象、情绪、场景等)

### 📁 智能命名
- 支持emoji数字解析 (1️⃣ → 1)
- 自动生成文件夹名称 (【序号+内容...】)
- 文件系统友好的字符清理

### 🔧 配置复用
- 智能查找现有项目配置
- 多来源API密钥加载
- 零配置启动体验

### 📊 默认脚本
- 内置完整的6段默认脚本
- 用户可选择使用或自定义
- 快速验证系统功能

## 🎮 使用方式

### 快速启动
```bash
./start.sh
```

### 手动启动
```bash
python3 run.py
```

### 选择脚本输入方式
- 选项1: 使用默认脚本 (推荐)
- 选项2: 自定义输入脚本

### 预期输出
```
data/output/
├── 【1狗都不，生...】/
├── 【2能自己喂肯...】/
├── 【3怕你走弯路...】/
├── 【4毕竟是宝宝...】/
├── 【5你就问问身...】/
└── 【6选奶关键的...】/
```

## 🔧 技术栈

- **Python 3.10+**: 主要编程语言
- **DeepSeek API**: AI语义分析
- **JSON处理**: 视频元数据解析
- **文件系统操作**: 智能文件组织
- **日志记录**: 完整的操作追踪

## 📈 扩展性

系统采用模块化设计，支持以下扩展：

- **新的AI提供商**: 通过实现新的客户端类
- **额外的匹配规则**: 通过修改动态配置
- **不同的文件组织方式**: 通过扩展file_organizer
- **新的数据源**: 通过实现新的分析器类

---

*最后更新: 2025-07-21* 