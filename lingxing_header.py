def set_header(login_info):
    headers = {
        'Content-Type': 'application/json',
        # 'Ak-Company-Id': '90136094793908736',
        # 'Ak-Request-Source': 'erp',
        # 'Ak-Env-Key': 'vayi',
        'Ak-Origin': 'https://vayi.lingxing.com',
        'Auth-Token': login_info['token'],
        'X-Ak-Company-Id': login_info['companyId'],
        # 'Accept': 'application/json, text/plain, */*',
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',

    }
    return headers