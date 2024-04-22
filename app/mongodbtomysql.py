import numpy as np
import pandas as pd
import pymongo
from sqlalchemy import create_engine

# MongoDB连接参数
mongo_uri = "mongodb://vayi:vayi12aBde@192.168.1.223:27017/"
mongo_db_name = "lingxing"

# MySQL连接参数
mysql_uri = 'mysql+pymysql://root:Dk03Bt3409abc@192.168.1.191:3306/api_access_token'

# 连接到MongoDB
mongo_client = pymongo.MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]

# 连接到MySQL
engine = create_engine(mysql_uri)


def flatten_data(data, parent_key='', sep='_'):
    """
    Flatten nested dictionaries and lists into a flat dictionary.
    """
    items = []
    if isinstance(data, list):
        for i, value in enumerate(data):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.extend(flatten_data(value, new_key, sep=sep))
    elif isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            items.extend(flatten_data(value, new_key, sep=sep))
    else:
        items.append((parent_key, data))
    return items

def flatten_df(df):
    """
    Flatten a DataFrame with nested lists and dictionaries into a flat DataFrame.
    """
    flat_records = []
    for _, row in df.iterrows():
        flat_record = {}
        for column, value in row.items():
            flat_items = flatten_data(value, parent_key=column, sep='_')
            flat_record.update(dict(flat_items))
        flat_records.append(flat_record)
    return pd.DataFrame(flat_records)


def process_collection_to_mysql(collection_name, mysql_table_name):
    """
    从MongoDB读取集合，扁平化数据，存储到MySQL表中。
    """
    collection = db[collection_name]
    data = list(collection.find())
    df = pd.DataFrame(data)
    flattened_df = flatten_df(df)

    # 存储到MySQL
    flattened_df.to_sql(mysql_table_name, con=engine, if_exists='replace', index=False)




# 扁平化嵌套字典
def flatten_nested_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_nested_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

if __name__ == "__main__":

    data = [
        {
            "_id": 122,
            "a": "abc",
            "b": {"a": "0000", "c": "11"},
            "c": [
                {"z": 1},
                {"z": 2}
            ]
        },
        {
            "_id": 333,
            "a": "abc2",
            "b": {"a": "0000", "c": "11"},
            "c": [
                {"z": 1},
                {"z": 2}
            ]
        }
    ]
    flat_data = []
    for item in data:
        flat_dict = flatten_nested_dict(item)  # 扁平化嵌套字典
        # 处理列表
        if 'c' in item and isinstance(item['c'], list):
            for sub_item in item['c']:
                sub_flat_dict = flat_dict.copy()
                sub_flat_dict.update(sub_item)
                flat_data.append(sub_flat_dict)
        else:
            flat_data.append(flat_dict)

    # 转换成 pandas DataFrame
    df = pd.DataFrame(flat_data)

    # 重命名列以匹配图像中的格式
    df.rename(columns={'_id': 'id'}, inplace=True)

    # 查看结果
    print(df)
# 示例使用
