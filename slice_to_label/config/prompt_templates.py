"""
统一提示词管理模块
支持动态优化、版本控制和多模型适配
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptTemplateManager:
    """统一提示词模板管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """初始化提示词管理器"""
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.prompt_file = self.config_dir / "prompt_templates.json"
        self.optimization_file = self.config_dir / "prompt_optimizations.json"
        
        # 加载提示词模板
        self.templates = self._load_templates()
        self.optimizations = self._load_optimizations()
        
        logger.info("✅ 统一提示词管理器初始化完成")
    
    def _load_templates(self) -> Dict[str, Any]:
        """加载基础提示词模板"""
        default_templates = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "templates": {
                # 🎯 第一阶段：通用交互识别（统一模板）
                "stage1_general_detection": {
                    "version": "1.2.0",
                    "description": "第一阶段通用交互识别 - 支持无人物场景，强制标准格式输出",
                    "prompt": """**重要：只输出以下三行，不要任何额外内容！**

interaction: [主语+动作+对象 或 物体状态描述]
scene: [场景位置]  
emotion: [情绪词或氛围词]

**示例输出：**
有人物时：
interaction: 宝宝哭闹拒绝奶瓶
scene: 医院走廊
emotion: 焦虑

无人物时：
interaction: 奶粉罐展示营养标签
scene: 家中厨房桌面
emotion: 专业

**要求：**
- 有人物：宝宝/妈妈/医生/护士 + 喝/哭/冲泡/展示/推荐/检查 + 奶粉/奶瓶/产品
- 无人物：奶粉罐/产品/包装/标签 + 展示/摆放/显示/突出 + 营养标签/品牌标识/成分信息
- 场景：医院/家中厨房/客厅/诊室/桌面/货架
- 情绪：开心/焦虑/平静/哭闹/温馨/专业/清新

**绝对禁止：**
- 详细分析段落
- 标题和编号
- 解释说明文字
- JSON或代码格式
- 超过三行的任何内容

**必须严格按照示例格式输出，只要三行！**""",
                    "optimization_notes": "通用模板，适用于Qwen和Gemini",
                    "last_optimized": datetime.now().isoformat()
                },
                
                # 🔍 第二阶段：品牌专用检测（统一模板）
                "stage2_brand_detection": {
                    "version": "1.0.0", 
                    "description": "第二阶段品牌识别 - 适用于所有视觉模型",
                    "prompt": """🔍 专业品牌识别分析师，请识别画面中的奶粉品牌标识。

**识别目标品牌列表：**
- 启赋 (Illuma)
- 蕴淳 (Wyeth Premium)  
- 惠氏 (Wyeth)
- A2 (A2 Platinum)


**识别要求：**
1. 品牌标识必须清晰可见
2. 仅识别目标列表中的品牌
3. 包装、罐体、标签上的品牌名称或Logo
4. 如无明确品牌标识输出"无"

**输出格式：**
品牌名称 或 "无\"""",
                    "optimization_notes": "品牌检测统一模板",
                    "last_optimized": datetime.now().isoformat()
                }
            }
        }
        
        if self.prompt_file.exists():
            try:
                with open(self.prompt_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载提示词模板失败，使用默认模板: {e}")
                
        # 保存默认模板
        self._save_templates(default_templates)
        return default_templates
    
    def _load_optimizations(self) -> Dict[str, Any]:
        """加载提示词优化历史"""
        if self.optimization_file.exists():
            try:
                with open(self.optimization_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载优化历史失败: {e}")
        
        return {
            "optimization_history": [],
            "current_version": "1.0.0",
            "total_optimizations": 0
        }
    
    def get_prompt(self, template_name: str, model_type: str = "universal") -> str:
        """获取指定模板的提示词"""
        try:
            template = self.templates["templates"].get(template_name)
            if not template:
                logger.error(f"未找到提示词模板: {template_name}")
                return ""
            
            # 统一模板，所有模型使用相同提示词
            prompt = template["prompt"]
            
            # 记录使用情况
            logger.debug(f"获取提示词: {template_name} (模型: {model_type})")
            
            return prompt
            
        except Exception as e:
            logger.error(f"获取提示词失败: {e}")
            return ""
    
    def optimize_prompt(self, template_name: str, feedback_data: Dict[str, Any], optimization_reason: str) -> bool:
        """基于反馈数据优化提示词"""
        try:
            logger.info(f"🔧 开始优化提示词: {template_name}")
            
            # 分析反馈数据
            optimization_suggestions = self._analyze_feedback_for_optimization(feedback_data)
            
            if not optimization_suggestions:
                logger.info("反馈数据质量良好，无需优化提示词")
                return False
            
            # 应用优化
            optimized = self._apply_optimization(template_name, optimization_suggestions, optimization_reason)
            
            if optimized:
                # 记录优化历史
                self._record_optimization(template_name, optimization_suggestions, optimization_reason)
                logger.success(f"✅ 提示词优化完成: {template_name}")
                return True
            else:
                logger.warning(f"⚠️  提示词优化失败: {template_name}")
                return False
                
        except Exception as e:
            logger.error(f"提示词优化异常: {e}")
            return False
    
    def _analyze_feedback_for_optimization(self, feedback_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析反馈数据生成优化建议"""
        suggestions = []
        
        modification_segments = feedback_data.get('modification_segments', [])
        if not modification_segments:
            return suggestions
        
        # 分析交互识别错误
        interaction_errors = [
            seg for seg in modification_segments 
            if any(keyword in seg.get('modification_reason', '') 
                  for keyword in ['交互', '行为', '主谓宾', '动作'])
        ]
        
        if len(interaction_errors) > 2:
            suggestions.append({
                "type": "interaction_enhancement",
                "issue": "交互识别准确性不足",
                "suggestion": "强化主谓宾结构识别，增加动作词汇精确性要求",
                "affected_count": len(interaction_errors)
            })
        
        # 分析情绪识别错误
        emotion_errors = [
            seg for seg in modification_segments
            if any(keyword in seg.get('modification_reason', '')
                  for keyword in ['情绪', '表情', '感情', '心情'])
        ]
        
        if len(emotion_errors) > 2:
            suggestions.append({
                "type": "emotion_enhancement", 
                "issue": "情绪识别深度不够",
                "suggestion": "加强微表情分析，强调真实情绪vs表面情绪的区分",
                "affected_count": len(emotion_errors)
            })
        
        # 分析场景识别错误
        scene_errors = [
            seg for seg in modification_segments
            if any(keyword in seg.get('modification_reason', '')
                  for keyword in ['场景', '环境', '地点', '背景'])
        ]
        
        if len(scene_errors) > 1:
            suggestions.append({
                "type": "scene_enhancement",
                "issue": "场景描述不够精确", 
                "suggestion": "增加空间定位精确性，细化环境描述要求",
                "affected_count": len(scene_errors)
            })
        
        return suggestions
    
    def _apply_optimization(self, template_name: str, suggestions: List[Dict[str, Any]], reason: str) -> bool:
        """应用优化建议到提示词模板"""
        try:
            template = self.templates["templates"].get(template_name)
            if not template:
                return False
            
            current_prompt = template["prompt"]
            optimized_prompt = current_prompt
            optimization_applied = []
            
            for suggestion in suggestions:
                if suggestion["type"] == "interaction_enhancement":
                    # 优化交互识别部分
                    if "动词识别规则" in optimized_prompt:
                        optimized_prompt = optimized_prompt.replace(
                            "- 精确动作词：喝、拒绝、冲泡、展示、推荐、哭闹、拥抱、观察、检查、测量",
                            "- 精确动作词：喝、拒绝、冲泡、展示、推荐、哭闹、拥抱、观察、检查、测量、抚摸、安抚、喂食\n   - 动作强度：轻柔、用力、急促、缓慢、仔细、粗暴"
                        )
                        optimization_applied.append("增强动作词汇精确性")
                
                elif suggestion["type"] == "emotion_enhancement":
                    # 优化情绪识别部分
                    if "情绪判断要点" in optimized_prompt:
                        optimized_prompt = optimized_prompt.replace(
                            "**情绪判断要点：**\n   - 观察面部表情细节\n   - 分析肢体语言信号\n   - 不被表面温馨误导\n   - 识别真实的情绪反应",
                            "**情绪判断要点：**\n   - 观察面部表情细节（眉毛、眼神、嘴角）\n   - 分析肢体语言信号（手势、姿态、动作幅度）\n   - 不被表面温馨误导，深入分析真实感受\n   - 识别微妙的不适、抗拒或满足信号\n   - 区分主动情绪vs被动反应"
                        )
                        optimization_applied.append("增强情绪识别深度")
                
                elif suggestion["type"] == "scene_enhancement":
                    # 优化场景描述部分
                    if "室内环境" in optimized_prompt:
                        optimized_prompt = optimized_prompt.replace(
                            "- 室内环境：家中厨房、客厅、卧室、餐厅",
                            "- 室内环境：家中厨房（操作台、水槽区）、客厅（沙发区、地毯区）、卧室（床边、窗边）、餐厅（餐桌、高椅）"
                        )
                        optimization_applied.append("增强场景描述精确性")
            
            if optimization_applied:
                # 更新模板
                template["prompt"] = optimized_prompt
                template["version"] = self._increment_version(template["version"])
                template["last_optimized"] = datetime.now().isoformat()
                template["optimization_notes"] = f"优化内容: {', '.join(optimization_applied)} | 原因: {reason}"
                
                # 保存更新
                self._save_templates(self.templates)
                
                logger.info(f"✅ 应用优化: {', '.join(optimization_applied)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"应用优化失败: {e}")
            return False
    
    def _increment_version(self, current_version: str) -> str:
        """递增版本号"""
        try:
            parts = current_version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        except:
            return "1.0.1"
    
    def _record_optimization(self, template_name: str, suggestions: List[Dict[str, Any]], reason: str):
        """记录优化历史"""
        optimization_record = {
            "timestamp": datetime.now().isoformat(),
            "template_name": template_name,
            "reason": reason,
            "suggestions": suggestions,
            "version_before": self.templates["templates"][template_name].get("version", "unknown"),
            "version_after": self.templates["templates"][template_name]["version"]
        }
        
        self.optimizations["optimization_history"].append(optimization_record)
        self.optimizations["total_optimizations"] += 1
        self.optimizations["current_version"] = self.templates["version"]
        
        # 保存优化历史
        with open(self.optimization_file, 'w', encoding='utf-8') as f:
            json.dump(self.optimizations, f, ensure_ascii=False, indent=2)
    
    def _save_templates(self, templates: Dict[str, Any]):
        """保存提示词模板"""
        templates["last_updated"] = datetime.now().isoformat()
        
        with open(self.prompt_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化总结"""
        return {
            "total_optimizations": self.optimizations.get("total_optimizations", 0),
            "current_version": self.templates.get("version", "1.0.0"),
            "templates_count": len(self.templates.get("templates", {})),
            "last_optimization": self.optimizations.get("optimization_history", [{}])[-1].get("timestamp", "从未优化")
        }

# 全局提示词管理器实例
_prompt_manager = None

def get_prompt_manager() -> PromptTemplateManager:
    """获取全局提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager()
    return _prompt_manager

def get_unified_prompt(template_name: str, model_type: str = "universal") -> str:
    """获取统一提示词（便捷函数）"""
    return get_prompt_manager().get_prompt(template_name, model_type)

def optimize_prompts_from_feedback(feedback_file: str, reason: str = "用户反馈优化") -> Dict[str, bool]:
    """基于反馈文件优化所有相关提示词"""
    try:
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedback_data = json.load(f)
        
        manager = get_prompt_manager()
        results = {}
        
        # 优化第一阶段提示词
        results["stage1_general_detection"] = manager.optimize_prompt(
            "stage1_general_detection", 
            feedback_data, 
            reason
        )
        
        # 如果有品牌相关错误，也优化第二阶段
        brand_errors = any(
            "品牌" in seg.get('modification_reason', '') or "标识" in seg.get('modification_reason', '')
            for seg in feedback_data.get('modification_segments', [])
        )
        
        if brand_errors:
            results["stage2_brand_detection"] = manager.optimize_prompt(
                "stage2_brand_detection",
                feedback_data,
                f"{reason} - 品牌识别优化"
            )
        
        return results
        
    except Exception as e:
        logger.error(f"批量优化提示词失败: {e}")
        return {} 

# 简化版Gemini专用prompt - 直接输出标准格式，避免复杂解析
GEMINI_SIMPLE_PROMPT = """🎯 你是专业的母婴视频分析师，请分析视频内容并严格按照以下格式输出：

**🎯 分析策略**：
- 仔细观察画面中的所有元素，无论是否有人物都要详细描述
- 有人物时：重点分析人物行为、交互、情绪
- 无人物时：重点描述产品特征、品牌元素、环境信息等有价值内容
- 避免"视频内容"等通用词汇，必须具体描述可见元素

**📋 分析要求**：
1. **interaction（核心）**：用"主语+动词+宾语"描述画面中的主要内容
   - 有人物：如"宝宝开心喝奶"、"妈妈冲泡奶粉"
   - 无人物：如"奶粉罐展示营养标签"、"产品突出品牌标识"
2. **scene**：描述具体的场景环境
3. **emotion**：识别画面传达的情绪或氛围
4. **brand_elements**：识别画面中的品牌元素，没有则填"无"

**✅ 输出格式（严格遵循）**：
interaction: [具体的行为描述或物体状态]
scene: [具体的场景描述]  
emotion: [单个情绪词或氛围词]
brand_elements: [品牌名称或"无"]

**⚠️ 注意**：
- 直接输出上述4行，不要添加其他文字
- 不要使用JSON格式
- 不要使用"视频"、"内容"等通用词汇
- 必须具体描述可见的元素和特征""" 