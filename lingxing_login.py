import asyncio
from datetime import datetime
from functools import wraps
import aiofiles
import httpx
import json
import uuid
from gen_sensors_anonymous_id import generate_sensor_id
from lingxingpwd import encrypt_password
import os

# 全局变量用于存储认证数据
global_auth_data = None

async def login():
    global global_auth_data

    if global_auth_data:
        if datetime.now().timestamp() - global_auth_data['timestamp'] < 430000:
            return global_auth_data

    file_path = "auth.json"
    if os.path.exists(file_path):
        print("读取认证文件")
        async with aiofiles.open(file_path, "r") as file:  # 使用aiofiles进行异步文件操作
            content = await file.read()
            data=json.loads(content)
            if datetime.now().timestamp() - data['timestamp'] < 430000:
                global_auth_data = data
                return global_auth_data

    print("重新登录")
    get_login_seckey_url = "https://gw.lingxingerp.com/newadmin/api/passport/getLoginSecretKey"
    login_url = "https://gw.lingxingerp.com/newadmin/api/passport/login"
    user_name = "vayiapi"
    password = "7KYx#ChlWu8d6]}T"
    headers = {
        'Content-Type': 'application/json',
        'Ak-Origin': 'https://vayi.lingxing.com',
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(get_login_seckey_url)

        login_json_data = {
            "account": user_name,
            "pwd": encrypt_password(password, response.json()["data"]["secretKey"]),  
            "verify_code": "",
            "uuid": str(uuid.uuid4()),
            "auto_login": 1,
            "sensorsAnonymousId": generate_sensor_id(),  
            "secretId": response.json()["data"]["secretId"]
        }

        try:
            login_response = await client.post(login_url, json=login_json_data, headers=headers)
            response_json = login_response.json()
            if response_json['companyId'] == '90136094793908736':
                response_json['timestamp'] = datetime.now().timestamp()
                async with aiofiles.open("auth.json", "w") as file:  # 使用aiofiles进行异步文件操作
                    await file.write(json.dumps(response_json, indent=4))
                global_auth_data = response_json
                return response_json
            else:
                print(f"登录失败: {response_json}")
        except httpx.RequestError as e:
            print(f"请求过程中出现问题: {e}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP状态错误: {e}")
        except Exception as e:
            print(f"处理响应时出现问题: {e}")

def before_call_login(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        login_info = await login()  # 使用await来调用异步的login函数
        return await func(login_info, *args, **kwargs)  # 确保func也是异步的
    return wrapper

    
if __name__ == "__main__":
    asyncio.run(login())
    print(global_auth_data)

