import genson
import json

import pandas as pd

# 你的 JSON 数据
data = {
    "code": 1,
    "msg": "操作成功",
    "require_id": "30A677CE-590D-5549-C894-9D0812A94182",
    "info": {
        "id": 27995,
        "zid": 1,
        "cid": 1057,
        "sku": "VYMB3137LKD1M",
        "product_name": "电脑背包/1#黑色/77#米白色/836#橘棕色/15.6寸",
        "model": "",
        "bid": 1001,
        "pic_url": "",
        "unit": "",
        "is_matched_alibaba": 0,
        "remark": "",
        "purchase_remark": "",
        "description": "",
        "clean_description": "",
        "special_attr": [],
        "product_developer_uid": 142,
        "product_developer": "陈婉怡",
        "product_designer": "",
        "product_presenter": "",
        "attachment_id": "",
        "status": 1,
        "open_status": 1,
        "update_time": 1708929615,
        "create_time": "2024-02-26 14:40",
        "bg_customs_export_name": "双肩包",
        "bg_customs_export_price": "0.000000",
        "bg_export_hs_code": "4202129000",
        "bg_customs_import_name": "Backpack",
        "bg_customs_import_price": "9.690000",
        "bg_import_hs_code": "",
        "bg_tax_rate": "0.0000",
        "cg_opt_uid": 113,
        "cg_opt_username": "李淑云",
        "product_creator_uid": 40,
        "cg_price": "63.0000",
        "cg_price_next_statis_time": 0,
        "cg_price_version": 0,
        "php_cg_price_next_statis_time": 1999999999,
        "cg_pallet_pcs": 0,
        "cg_product_material": "100%涤纶",
        "cg_delivery": 0,
        "cg_transport_costs": "0.00",
        "link_num": 0,
        "is_combo": 1,
        "combo_level": 1,
        "is_aux": 0,
        "product_type": 2,
        "is_delete": 0,
        "gmt_modified": "2024-02-26 14:42:25",
        "gmt_create": "2024-02-26 14:40:15",
        "primary_supplier_id": 300,
        "currency": "USD",
        "is_related": 0,
        "unit_process_fee": "0.0000",
        "process_remark": "",
        "attribute": "",
        "ps_id": 0,
        "spu": "",
        "spu_name": "",
        "is_migrate": 0,
        "v_uuid": "C9142AC8-B8F1-4BA1-8F27-B2D60A1E6F84",
        "company_id": 90136094793908736,
        "aux_relation_list": [],
        "brand_name": "LOVEVOOK",
        "status_text": "在售",
        "category_name": "电脑背包",
        "product_declaration_list": {
            "customs_import_price": "9.69",
            "customs_import_price_currency": "USD",
            "customs_import_price_currency_icon": "$",
            "customs_export_name": "双肩包",
            "customs_import_name": "Backpack",
            "customs_declaration_unit": "",
            "customs_declaration_spec": "",
            "customs_declaration_origin_produce": "",
            "customs_declaration_inlands_source": "",
            "customs_declaration_exempt": "",
            "other_declare_element": "",
            "customs_declaration_hs_code": "4202129000"
        },
        "product_clearance_list": {
            "customs_clearance_material": "",
            "customs_clearance_usage": "",
            "customs_clearance_internal_code": "",
            "customs_clearance_preferential": 0,
            "customs_clearance_preferential_text": "",
            "customs_clearance_brand_type": 0,
            "customs_clearance_brand_type_text": "",
            "customs_clearance_product_pattern": "",
            "customs_clearance_pic_url": "",
            "allocation_remark": "",
            "weaving_mode": 0,
            "weaving_mode_text": "",
            "customs_clearance_price": "0.00",
            "customs_clearance_price_currency": "CNY",
            "customs_clearance_price_currency_icon": "￥",
            "customs_clearance_hs_code": "",
            "customs_clearance_tax_rate": "0.0000",
            "customs_clearance_remark": ""
        },
        "product_logistics_list": [],
        "supplier_list": [
            {
                "psq_id": "210414626675302915",
                "product_id": "27995",
                "supplier_id": "300",
                "is_primary": 1,
                "supplier_product_url": [],
                "quote_remark": "",
                "quote_cg_delivery": 0,
                "cg_price": "63.0000",
                "cg_currency_icon": "￥",
                "supplier_name": "金蝶推送虚拟供应商",
                "supplier_code": "SU00265",
                "level_text": "",
                "employees_text": "",
                "remark": "",
                "quotes": [
                    {
                        "currency": "CNY",
                        "currency_icon": "￥",
                        "is_tax": 0,
                        "tax_rate": "0.00",
                        "step_prices": [
                            {
                                "moq": 0,
                                "price": "0.0000",
                                "price_with_tax": "0.0000"
                            }
                        ]
                    }
                ],
                "permission_type": 1
            }
        ],
        "list": [
            {
                "product_id": 27988,
                "pic_url": "",
                "sku": "SPVYMB3137LKD1M",
                "product_name": "电脑背包/1#黑色/77#米白色/836#橘棕色/15.6寸",
                "model": "",
                "unit": "",
                "special_attr": [],
                "cg_delivery": 0,
                "cg_product_length": "0.00",
                "cg_product_width": "0.00",
                "cg_product_height": "0.00",
                "cg_product_net_weight": "0.0000",
                "cg_product_gross_weight": "0.0000",
                "cg_product_material": "",
                "quantity": 1,
                "cg_price": "0.0000",
                "logistics": [],
                "is_combo": 0
            }
        ],
        "permission_user_info": [
            {
                "permission_uid": 40,
                "realname": "罗秋鑫"
            }
        ],
        "product_creator_realname": "罗秋鑫",
        "picture_list": [],
        "qc_standard": {
            "qc_method": 1,
            "qc_method_text": "抽检",
            "pqt_id": "",
            "system_qc_template": {
                "pqt_id": "",
                "name": "",
                "qc_image": [],
                "template_item": [
                    {
                        "pqti_id": "",
                        "qc_item": "",
                        "sort": "",
                        "qc_content": [],
                        "create_time": ""
                    }
                ]
            },
            "custom_qc_template": {
                "pqt_id": "",
                "name": "",
                "qc_image": [],
                "template_item": [
                    {
                        "pqti_id": "",
                        "qc_item": "",
                        "sort": "",
                        "qc_content": [],
                        "create_time": ""
                    }
                ]
            }
        },
        "global_tags": [],
        "spec_info": {
            "product_id": 27995,
            "ps_id": "210414626675302913",
            "spec_unit": "SI",
            "cg_product_spec_unit": "cm",
            "cg_product_net_weight_unit": "g",
            "cg_product_length": "0.00",
            "cg_product_width": "0.00",
            "cg_product_height": "0.00",
            "cg_product_net_weight": "0.0000",
            "spec_pack_list": [
                {
                    "pps_id": "210414626675302912",
                    "spec_title": "默认箱规",
                    "is_default": 1,
                    "cg_box_spec_unit": "cm",
                    "cg_box_length": "0.00",
                    "cg_box_width": "0.00",
                    "cg_box_height": "0.00",
                    "cg_box_weight": "0.0000",
                    "cg_box_weight_unit": "kg",
                    "cg_box_pcs": "0",
                    "cg_package_length": "0.00",
                    "cg_package_width": "0.00",
                    "cg_package_height": "0.00",
                    "cg_package_spec_unit": "cm",
                    "cg_product_gross_weight": "0.7000",
                    "cg_product_gross_weight_unit": "g"
                }
            ]
        },
        "product_match_alibaba": [],
        "attachmentFiles": [],
        "custom_fields": []
    },
    "req_time_sequence": "/listing-api/api/product/showOnline$$1",
    "update_code": 1
}

# 创建一个 SchemaBuilder 对象
builder = genson.SchemaBuilder()

# 将 JSON 数据添加到 Schema Builder
builder.add_object(data)

# 生成 JSON Schema
schema = builder.to_schema()

# 打印生成的 JSON Schema
print(json.dumps(schema, indent=2))

df = pd.json_normalize(data,record_path=['info'])
pd.set_option('display.max_columns', None)
print(df)
