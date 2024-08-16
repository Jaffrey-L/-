from k3cloud_webapi_sdk.main import K3CloudApiSdk


class Ext_k3sdk(K3CloudApiSdk):
    def stock_report(self, data):
        """
        扩展分页报表查询功能
        :param data: 查询所需的参数，格式如下,构造时只需构造，parameters 里面的对象：
        {
            "parameters": [
                {
                    "FORMID": "STK_InvAgeDetailRpt",
                    "FSCHEMEID": "6656ce15dc549d",
                    "QuicklyCondition": []
                }
            ]
        }
        :return: 库存报表的查询结果
        """
        return self.Execute(
            'Kingdee.K3.SCM.WebApi.ServicesStub.StockReportQueryService.GetReportData,Kingdee.K3.SCM.WebApi.ServicesStub',
            {"parameters": [data]})
