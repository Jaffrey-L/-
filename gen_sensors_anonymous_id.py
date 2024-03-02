import uuid
import random

def generate_sensor_id():
    # 生成两个随机的UUID字符串并去除破折号
    uuid_part1 = uuid.uuid4().hex[:16]
    uuid_part2 = uuid.uuid4().hex[:16]
    
    # 生成中间部分的随机数字，模拟示例中的结构
    middle_part1 = random.randint(1000000, 9999999)
    middle_part2 = random.randint(1000000, 9999999)
    middle_part3 = random.randint(100000, 999999)
    middle_part4 = random.randint(1000000, 9999999)
    
    # 生成最后的十六进制字符串部分
    hex_suffix = ''.join(random.choices('0123456789abcdef', k=14))
    
    # 拼接所有部分
    custom_id = f"{uuid_part1}-{uuid_part2}-{middle_part1}-{middle_part2}-{middle_part3}-{middle_part4}-{hex_suffix}"
    
    return custom_id

# 测试函数
if __name__ == "__main__":
    custom_id = generate_sensor_id()
    print(custom_id)

