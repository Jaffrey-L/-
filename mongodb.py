from pymongo import MongoClient

client = MongoClient('mongodb://192.168.1.181:27017/')
db = client['lingxing']  # 替换为你的数据库名

def close_mongo_connection():
    client.close()