import datetime

from app.AsyncPostgres import AsyncPostgres


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def fetch_sids():
    async with AsyncPostgres() as conn:
        sql = "select DISTINCT sid from lx_sellers order by sid"
        rows = await conn.fetch(sql)
        sid_list = [row['sid'] for row in rows]

        # 将 sid_list 分批处理，每批 200 条
        sid_batches = list(chunks(sid_list, 200))

        result_batches = [{"sid": batch} for batch in sid_batches]
        return result_batches


# 函数：生成指定日期范围内的每一天
def daterange(start_date: str, end_date: str):
    # 将日期字符串转换为 datetime.date 对象
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    for n in range(int((end - start).days) + 1):
        yield start + datetime.timedelta(n)
