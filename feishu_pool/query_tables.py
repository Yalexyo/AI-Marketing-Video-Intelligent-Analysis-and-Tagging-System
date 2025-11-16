"""
飞书多维表格查询工具
用于查询指定应用中的所有表格信息
"""

import json
import time
from typing import Dict, List, Optional, Any
import requests
from urllib.parse import urljoin

class FeishuTableQuery:
    """飞书多维表格查询器"""
    
    def __init__(self, config_path: str = "optimized_pool_config.json"):
        """初始化表格查询器"""
        self.config = self._load_config(config_path)
        self.app_id = self.config.get('feishu_api', {}).get('app_id')
        self.app_secret = self.config.get('feishu_api', {}).get('app_secret')
        self.access_token = None
        self.access_token_expires = 0
        
        # 飞书API基础URL
        self.base_url = "https://open.feishu.cn/open-apis"
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}
    
    def get_access_token(self) -> str:
        """获取访问令牌"""
        current_time = int(time.time())
        
        # 如果token还有效，直接返回
        if self.access_token and current_time < self.access_token_expires - 60:
            return self.access_token
        
        # 获取新的token
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                self.access_token = result["app_access_token"]
                self.access_token_expires = current_time + result["expire"]
                return self.access_token
            else:
                raise Exception(f"获取token失败: {result}")
                
        except Exception as e:
            print(f"❌ 获取访问令牌失败: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送API请求"""
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"API调用失败: {result}")
            
            return result
            
        except Exception as e:
            print(f"❌ API请求失败 [{method} {endpoint}]: {e}")
            raise
    
    def get_app_info(self, app_token: str) -> Dict[str, Any]:
        """获取应用基本信息"""
        endpoint = f"bitable/v1/apps/{app_token}"
        return self._make_request("GET", endpoint)
    
    def list_tables(self, app_token: str) -> List[Dict[str, Any]]:
        """获取应用中的所有表格"""
        endpoint = f"bitable/v1/apps/{app_token}/tables"
        
        try:
            result = self._make_request("GET", endpoint)
            tables = result.get("data", {}).get("items", [])
            
            print(f"📊 表格列表 (共 {len(tables)} 个):")
            print("="*60)
            
            for i, table in enumerate(tables, 1):
                table_id = table.get("table_id", "未知")
                table_name = table.get("name", "未知")
                revision = table.get("revision", "未知")
                
                print(f"  {i}. 表格名称: {table_name}")
                print(f"     表格ID: {table_id}")
                print(f"     版本号: {revision}")
                print("-"*40)
            
            return tables
            
        except Exception as e:
            print(f"❌ 获取表格列表失败: {e}")
            return []
    
    def get_table_details(self, app_token: str, table_id: str) -> Dict[str, Any]:
        """获取表格详细信息"""
        # 获取表格基本信息
        table_endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}"
        
        try:
            table_result = self._make_request("GET", table_endpoint)
            table_info = table_result.get("data", {}).get("table", {})
            
            # 获取字段信息
            fields_endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            fields_result = self._make_request("GET", fields_endpoint)
            fields = fields_result.get("data", {}).get("items", [])
            
            # 获取视图信息
            views_endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/views"
            views_result = self._make_request("GET", views_endpoint)
            views = views_result.get("data", {}).get("items", [])
            
            # 获取记录总数（只获取第一页来估算）
            records_endpoint = f"bitable/v1/apps/{app_token}/tables/{table_id}/records"
            try:
                records_result = self._make_request("GET", records_endpoint, params={"page_size": 1})
                total_records = records_result.get("data", {}).get("total", 0)
            except:
                total_records = "无法获取"
            
            detailed_info = {
                "table_info": table_info,
                "fields_count": len(fields),
                "fields": fields,
                "views_count": len(views), 
                "views": views,
                "records_count": total_records
            }
            
            return detailed_info
            
        except Exception as e:
            print(f"❌ 获取表格详细信息失败: {e}")
            return {}
    
    def get_comprehensive_summary(self, app_token: str) -> Dict[str, Any]:
        """获取应用的综合摘要信息"""
        try:
            # 获取应用信息
            print("🔍 获取应用基本信息...")
            app_info_result = self.get_app_info(app_token)
            app_info = app_info_result.get("data", {})
            
            # 获取表格列表
            print("\n📊 获取表格列表...")
            tables = self.list_tables(app_token)
            
            # 统计信息
            summary = {
                "app_info": {
                    "name": app_info.get("name", "未知"),
                    "app_token": app_token,
                    "url": app_info.get("url", ""),
                    "is_advanced": app_info.get("is_advanced", False),
                    "time_zone": app_info.get("time_zone", "")
                },
                "tables_summary": {
                    "total_tables": len(tables),
                    "tables": []
                }
            }
            
            # 获取每个表格的详细信息
            if tables:
                print(f"\n📋 获取 {len(tables)} 个表格的详细信息...")
                
                for i, table in enumerate(tables, 1):
                    table_id = table.get("table_id")
                    table_name = table.get("name", "未知")
                    
                    print(f"   {i}/{len(tables)} 处理表格: {table_name}")
                    
                    try:
                        details = self.get_table_details(app_token, table_id)
                        
                        table_summary = {
                            "table_id": table_id,
                            "table_name": table_name,
                            "fields_count": details.get("fields_count", 0),
                            "views_count": details.get("views_count", 0),
                            "records_count": details.get("records_count", "未知"),
                            "revision": table.get("revision", "未知")
                        }
                        
                        summary["tables_summary"]["tables"].append(table_summary)
                        
                    except Exception as e:
                        print(f"      ❌ 获取表格 {table_name} 详情失败: {e}")
                        
                        table_summary = {
                            "table_id": table_id,
                            "table_name": table_name,
                            "error": str(e)
                        }
                        summary["tables_summary"]["tables"].append(table_summary)
            
            return summary
            
        except Exception as e:
            print(f"❌ 获取综合摘要失败: {e}")
            return {}
    
    def export_summary_report(self, app_token: str, output_file: str = None) -> str:
        """导出摘要报告"""
        if not output_file:
            timestamp = int(time.time())
            output_file = f"feishu_tables_summary_{timestamp}.json"
        
        print("📋 开始生成表格摘要报告...")
        summary = self.get_comprehensive_summary(app_token)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 表格摘要报告已导出: {output_file}")
            
            # 打印摘要
            if summary.get("app_info"):
                app_name = summary["app_info"].get("name", "未知")
                total_tables = summary.get("tables_summary", {}).get("total_tables", 0)
                
                print(f"\n📈 应用摘要:")
                print(f"   应用名称: {app_name}")
                print(f"   表格总数: {total_tables}")
                
                if summary.get("tables_summary", {}).get("tables"):
                    print(f"   表格详情:")
                    for table in summary["tables_summary"]["tables"]:
                        name = table.get("table_name", "未知")
                        fields = table.get("fields_count", "未知")
                        records = table.get("records_count", "未知")
                        print(f"     • {name}: {fields}字段, {records}记录")
            
            return output_file
            
        except Exception as e:
            print(f"❌ 导出摘要报告失败: {e}")
            return ""

def main():
    """主函数 - 表格查询工具演示"""
    try:
        # 初始化表格查询器
        query_tool = FeishuTableQuery()
        
        # 从配置文件获取应用token
        config = query_tool.config
        app_token = config.get('feishu_api', {}).get('app_token')
        
        if not app_token:
            print("❌ 未找到应用token，请检查配置文件")
            return
        
        print(f"🚀 飞书表格查询工具启动")
        print(f"📱 应用Token: {app_token}")
        print("="*60)
        
        # 获取应用信息
        print("🔍 获取应用基本信息...")
        app_info_result = query_tool.get_app_info(app_token)
        app_info = app_info_result.get("data", {})
        app_name = app_info.get("name", "未知")
        
        print(f"📋 应用名称: {app_name}")
        print(f"🌐 应用URL: {app_info.get('url', '未知')}")
        
        # 获取表格列表
        print(f"\n📊 获取表格列表...")
        tables = query_tool.list_tables(app_token)
        
        if tables:
            print(f"\n📈 总结: 应用 '{app_name}' 中共有 {len(tables)} 个表格")
        else:
            print(f"\n❌ 未找到任何表格或无权限访问")
        
        # 导出详细报告
        print(f"\n📄 导出详细摘要报告...")
        report_file = query_tool.export_summary_report(app_token)
        
        print(f"\n✅ 表格查询完成")
        
    except Exception as e:
        print(f"❌ 表格查询工具运行失败: {e}")

if __name__ == "__main__":
    main() 