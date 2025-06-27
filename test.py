import requests
import json
from openai import OpenAI
from datetime import datetime

# 初始化OpenAI客户端
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="583ca88d-ba68-401d-ae86-f5b6d87ef08f"
)

# 高德天气API配置
GAODE_API_KEY = "c8c31e524a0aaa6297ce0cf4a684059e"
WEATHER_URL = "https://restapi.amap.com/v3/weather/weather_info"

# 网页搜索API配置
WEB_SEARCH_API_URL = "https://api.bochaai.com/v1/web-search"
WEB_SEARCH_API_KEY = "sk-5635f459fa3c4e31b4a835678597649e"

# 定义天气查询工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当且仅当用户需要获取天气信息时，获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称或行政区划代码，如'北京'或'110101'"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当且仅当用户需要获取当前时间时，获取本地当前时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "当用户查询需要最新实时信息、新闻、未知事实或模型无法回答的问题时，使用网页搜索获取最新信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的关键词或问题"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回的结果数量，默认为3",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def get_current_weather(location):
    """调用高德地图API查询天气"""
    params = {
        "key": GAODE_API_KEY,
        "city": location,
        "extensions": "base"
    }
    try:
        response = requests.get(WEATHER_URL, params=params)
        result = response.json()
        
        # 处理API响应
        if result.get("status") == "1" and result.get("count") != "0":
            weather_data = result["lives"][0]
            return json.dumps({
                "status": "success",
                "location": f"{weather_data['province']}{weather_data['city']}",
                "weather": weather_data["weather"],
                "temperature": weather_data["temperature"],
                "wind": f"{weather_data['winddirection']}风{weather_data['windpower']}级",
                "humidity": f"{weather_data['humidity']}%",
                "report_time": weather_data["reporttime"]
            }, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "message": "未找到该城市天气信息"})
            
    except Exception as e:
        return json.dumps({"status": "error", "message": f"API请求失败: {str(e)}"})

def get_current_time():
    """获取当前本地时间"""
    try:
        current_time = datetime.now()
        return json.dumps({
            "status": "success",
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": current_time.strftime("%A"),
            "date": current_time.strftime("%Y年%m月%d日"),
            "time": current_time.strftime("%H时%M分%S秒")
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"获取时间失败: {str(e)}"})

def web_search(query, count=3):
    """执行网页搜索并返回摘要信息"""
    try:
        payload = json.dumps({
            "query": query,
            "summary": True,
            "count": count
        })
        
        headers = {
            'Authorization': f'Bearer {WEB_SEARCH_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(WEB_SEARCH_API_URL, headers=headers, data=payload)
        result = response.json()
        
        if result.get('code') == 200 and 'data' in result:
            search_data = result['data']
            web_pages = search_data.get('webPages', {}).get('value', [])
            
            # 提取每个结果的摘要信息
            summaries = []
            for i, page in enumerate(web_pages[:count], 1):
                title = page.get('name', '无标题')
                url = page.get('url', '#')
                snippet = page.get('summary') or page.get('snippet', '无摘要信息')
                
                # 清理摘要中的特殊字符
                clean_snippet = snippet.replace('\ue50a', '').replace('\ue50b', '').strip()
                
                summaries.append({
                    "title": title,
                    "url": url,
                    "summary": clean_snippet
                })
            
            return json.dumps({
                "status": "success",
                "query": query,
                "results": summaries
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": f"搜索失败: {result.get('msg', '未知错误')}"
            })
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"搜索请求异常: {str(e)}"
        })

def run_agent(user_input):
    """运行智能体对话"""
    messages = [{"role": "system", "content":"你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"},
                {"role": "user", "content": user_input}]
    
    while True:
        # 调用模型获取响应
        response = client.chat.completions.create(
            model="doubao-seed-1-6-flash-250615",  # 修正了模型名称拼写错误
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        # 检查是否需要调用工具
        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_current_weather":
                    # 调用天气查询
                    weather_info = get_current_weather(function_args["location"])
                    
                    # 添加工具响应到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": weather_info
                    })
                
                elif function_name == "get_current_time":
                    # 调用时间查询
                    time_info = get_current_time()
                    
                    # 添加工具响应到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": time_info
                    })
                
                elif function_name == "web_search":
                    # 调用网页搜索
                    count = function_args.get("count", 3)
                    search_info = web_search(function_args["query"], count)
                    
                    # 添加工具响应到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": search_info
                    })
        else:
            # 没有工具调用时返回最终回复
            return message.content.strip()
    
    return "抱歉，处理您的请求时出现问题"

# 示例使用
if __name__ == "__main__":
    while True:
        user_input = input("\n用户: ")
        if user_input.lower() in ["退出", "exit", "quit"]:
            break
            
        response = run_agent(user_input)
        print(f"助手: {response}")