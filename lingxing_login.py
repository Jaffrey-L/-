from datetime import datetime
from functools import wraps
import httpx
import json
import uuid
from gen_sensors_anonymous_id import generate_sensor_id
from lingxingpwd import encrypt_password
import os

global_auth_data = {}

def  login():

    global global_auth_data

    if global_auth_data:
        if datetime.now().timestamp() - global_auth_data['timestamp'] < 430000:
            return global_auth_data

    file_path = "auth.json"
    if os.path.exists(file_path):
        print("读取认证文件")
        with open(file_path, "r") as file:
            data = json.load(file)
            if datetime.now().timestamp() - data['timestamp'] < 430000:
                global_auth_data = data
                return global_auth_data
            
    # 重新登录
    print("重新登录")
    get_login_seckey_url = "https://gw.lingxingerp.com/newadmin/api/passport/getLoginSecretKey"
    login_url="https://gw.lingxingerp.com/newadmin/api/passport/login"
    user_name="vayiapi"
    password="7KYx#ChlWu8d6]}T"
    headers = {
        'Content-Type': 'application/json',
        # 'Ak-Company-Id': '90136094793908736',
        # 'Ak-Request-Source': 'erp',
        # 'Ak-Env-Key': 'vayi',
        'Ak-Origin': 'https://vayi.lingxing.com',
        # 'Accept': 'application/json, text/plain, */*',
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',

    }

    # 获取登录密钥
    response = httpx.post(get_login_seckey_url)

    login_json_data = {
        "account": user_name,
        "pwd": encrypt_password(password, response.json()["data"]["secretKey"]),
        "verify_code": "",
        "uuid": str(uuid.uuid4()),
        "auto_login": 1,
        "sensorsAnonymousId": generate_sensor_id(),
        "secretId": response.json()["data"]["secretId"]
    }

    # 登录
    try:
        with httpx.Client(headers=headers) as client:
            login_response = client.post(login_url, json=login_json_data)
            response_json = login_response.json()
            if response_json['companyId'] == '90136094793908736':
                response_json['timestamp'] = datetime.now().timestamp()
                with open("auth.json", "w") as file:
                    json.dump(response_json, file, indent=4)
                return response_json
            else:
                print(f"登录失败:{response_json}")
    except httpx.RequestError as e:
        print(f"请求过程中出现问题: {e}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP状态错误: {e}")
    except Exception as e:
        print(f"处理响应时出现问题: {e}")


def before_call_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        login_info = login()  # 获取login函数的返回值
        return func(login_info, *args, **kwargs)  # 将login的返回值作为第一个参数传递给func
    return wrapper

    
if __name__ == "__main__":
    login()   
    print(global_auth_data)

