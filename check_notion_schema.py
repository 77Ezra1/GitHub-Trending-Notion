"""
检查Notion数据库结构的工具脚本
运行此脚本可以查看你的Notion数据库有哪些属性
"""

import requests
import json


def check_notion_database():
    import os
    from dotenv import load_dotenv

    load_dotenv()

    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        print("错误: 请在 .env 文件中设置 NOTION_TOKEN 和 NOTION_DATABASE_ID")
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    url = f"https://api.notion.com/v1/databases/{database_id}"

    print("正在获取Notion数据库结构...")
    print("=" * 60)

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        properties = data.get("properties", {})

        print(f"\n数据库标题: {data.get('title', [{}])[0].get('plain_text', 'N/A')}")
        print(f"\n数据库属性 ({len(properties)} 个):")
        print("-" * 60)

        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "unknown")
            print(f"  [{prop_type:12}] {prop_name}")

            # 对于select类型，显示选项
            if prop_type == "select" and "select" in prop_data:
                options = prop_data["select"].get("options", [])
                if options:
                    print(f"                选项: {', '.join([o['name'] for o in options])}")

        print("\n" + "=" * 60)
        print("请根据上面的属性名称，修改主脚本中的属性映射")
        print("=" * 60)

        # 保存到JSON文件
        with open("notion_schema.json", "w", encoding="utf-8") as f:
            json.dump(properties, f, indent=2, ensure_ascii=False)
        print("\n数据库结构已保存到 notion_schema.json")

    else:
        print(f"错误: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    check_notion_database()
