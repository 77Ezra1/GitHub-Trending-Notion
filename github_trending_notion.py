"""
GitHub Trending to Notion 自动化脚本
获取GitHub Trending热门项目，并写入Notion数据库
自动检测Notion数据库结构，智能匹配字段
"""

import requests
import json
import re
from datetime import datetime, timedelta
import time
import os
import sys
from difflib import get_close_matches
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 设置UTF-8编码（Windows兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class GitHubTrendingToNotion:
    def __init__(self):
        # Notion 配置（从环境变量读取）
        self.notion_token = os.getenv("NOTION_TOKEN", "")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID", "")
        self.notion_headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        # GitHub 配置
        self.github_token = os.getenv("GITHUB_TOKEN", "")

        # 火山引擎豆包 API 配置（从环境变量读取）
        self.volcano_api_key = os.getenv("VOLCANO_API_KEY", "")
        self.volcano_api_url = os.getenv("VOLCANO_API_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
        self.volcano_model = os.getenv("VOLCANO_MODEL", "")

        # 代理配置
        proxy = os.getenv("PROXY", "")
        if proxy:
            self.proxies = {
                "http": proxy,
                "https": proxy
            }
            print(f"📡 使用代理: {proxy}")
        else:
            self.proxies = None

        # 国内服务不走代理
        self.proxies_no_noproxy = None  # 火山引擎等国内服务

        # 数据库属性结构（运行时获取）
        self.db_properties = {}
        # 字段映射关系（运行时自动匹配）
        self.field_mapping = {}
        # 当前日期时间字符串（ISO 8601格式，带时间戳）
        self.current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Trending配置
        self.trending_url = "https://github.com/trending"
        self.trending_period = "daily"  # daily, weekly, monthly

        # AI分析缓存（避免重复分析同一仓库）
        self.analyzed_repos = {}

    def get_database_schema(self):
        """获取Notion数据库的结构"""
        url = f"https://api.notion.com/v1/databases/{self.notion_database_id}"

        try:
            response = requests.get(url, headers=self.notion_headers, proxies=self.proxies)
            response.raise_for_status()
            data = response.json()
            self.db_properties = data.get("properties", {})

            print("\n📊 Notion数据库结构:")
            print("=" * 50)
            for prop_name, prop_data in self.db_properties.items():
                prop_type = prop_data.get("type", "unknown")
                print(f"  [{prop_type:12}] {prop_name}")
            print("=" * 50)

            return True

        except requests.RequestException as e:
            print(f"✗ 获取数据库结构失败: {e}")
            return False

    def auto_match_fields(self):
        """自动匹配GitHub数据到Notion字段"""
        # 定义我们想写入的数据及其可能的字段名
        field_candidates = {
            "name": ["name", "title", "project", "repository", "repo", "项目名称", "名称"],
            "full_name": ["full name", "fullname", "full_name", "repo", "repository", "完整名称", "全名"],
            "description": ["description", "desc", "about", "summary", "intro", "描述", "简介"],
            "url": ["url", "link", "github", "github url", "repository url", "项目链接", "链接", "地址"],
            "stars": ["stars", "star", "stargazers", "星标数", "总星标数", "点赞数", "stars数"],
            "language": ["language", "lang", "编程语言", "语言", "技术栈", "tech stack"],
            "forks": ["forks", "fork", "fork count", "分支数", "fork数", "fork"],
            "owner": ["owner", "author", "creator", "maintainer", "用户", "作者", "所有者", "owner"],
            "created_at": ["created", "created at", "create date", "date created", "创建时间", "创建日期"],
            "updated_at": ["updated", "updated at", "last updated", "update date", "更新时间", "更新日期"],
            "open_issues": ["issues", "open issues", "issue count", "问题数", "issues数"],
            "topics": ["topics", "tags", "labels", "subject", "主题", "标签"],
            "license": ["license", "licence", "许可证", "授权"],
            "today_stars": ["今日新增", "today stars", "new stars"],
            "date": ["日期", "date", "时间", "time"],
            "repo_detail": ["仓库详情", "ai解析描述", "仓库描述", "ai description", "detail", "details", "ai总结", "ai摘要"],
        }

        # 获取数据库中所有的属性名
        db_prop_names = list(self.db_properties.keys())

        print("\n🔍 自动匹配字段:")
        print("-" * 50)

        # 记录已匹配的Notion字段，避免重复匹配
        matched_notion_props = set()

        for field_key, candidates in field_candidates.items():
            matched = None

            # 首先尝试精确匹配（不区分大小写）
            for prop_name in db_prop_names:
                if prop_name.lower() in [c.lower() for c in candidates] and prop_name not in matched_notion_props:
                    matched = prop_name
                    break

            # 如果没有精确匹配，尝试模糊匹配
            if not matched:
                # 将候选词转换为小写用于匹配
                candidates_lower = [c.lower() for c in candidates]
                for prop_name in db_prop_names:
                    if prop_name.lower() in candidates_lower and prop_name not in matched_notion_props:
                        matched = prop_name
                        break

            # 使用difflib进行模糊匹配
            if not matched and db_prop_names:
                available_props = [n for n in db_prop_names if n not in matched_notion_props]
                matches = get_close_matches(field_key, [n.lower() for n in available_props], n=1, cutoff=0.3)
                if matches:
                    # 找到原始大小写的名称
                    for prop_name in available_props:
                        if prop_name.lower() == matches[0]:
                            matched = prop_name
                            break

            if matched:
                self.field_mapping[field_key] = matched
                matched_notion_props.add(matched)
                prop_type = self.db_properties[matched].get("type", "")
                print(f"  ✓ {field_key:15} → {matched} ({prop_type})")
            else:
                print(f"  - {field_key:15} → (未找到匹配字段)")

        print("-" * 50)

        # 检查必需字段
        if "name" not in self.field_mapping:
            print("\n⚠️  警告: 未找到名称/标题字段，这是必需的！")
            print("请确保数据库有一个 title 类型的属性")
            return False

        return True

    def parse_number(self, text):
        """解析包含k、M等单位的数字字符串"""
        if not text:
            return 0
        text = text.strip().replace(',', '').replace(' ', '')
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        match = re.search(r'([\d.]+)([kmb]?)', text.lower())
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            return int(num * multipliers.get(unit, 1))
        return 0

    def get_trending_repos(self):
        """
        从GitHub Trending页面获取热门项目
        爬取 https://github.com/trending
        """
        print(f"\n正在爬取 GitHub Trending (周期: {self.trending_period})...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            # 可以添加语言筛选，例如 ?since=daily&language=python
            params = {
                "since": self.trending_period
            }

            response = requests.get(self.trending_url, params=params, headers=headers, timeout=30, proxies=self.proxies)
            response.raise_for_status()
            html = response.text

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('article', class_='Box-row')

            trending_repos = []
            for article in articles[:10]:  # 只取前10个
                repo_data = self.parse_repo_article_soup(article)
                if repo_data:
                    trending_repos.append(repo_data)

            print(f"✓ 成功获取 {len(trending_repos)} 个热门项目")
            return trending_repos

        except requests.RequestException as e:
            print(f"✗ 获取GitHub Trending失败: {e}")
            return []

    def parse_repo_article_soup(self, article):
        """使用BeautifulSoup解析单个项目的HTML"""
        try:
            # 查找主链接 (通常是h2或h3标签中的a标签)
            title_tag = article.find(['h2', 'h3'], class_='h3 lh-condensed')
            if not title_tag:
                title_tag = article.select_one('h2 a, h3 a')

            if not title_tag or not title_tag.find('a'):
                return None

            repo_link = title_tag.find('a')
            href = repo_link.get('href', '')
            name = repo_link.get_text(strip=True)

            # 从链接中提取owner和repo name
            # href格式: /owner/repo
            parts = href.strip('/').split('/')
            if len(parts) >= 2:
                owner = parts[0]
                repo_name = parts[1]
            else:
                return None

            full_name = f"{owner}/{repo_name}"
            url = f"https://github.com{href.strip()}"

            # 提取描述
            description = ""
            p_tag = article.find('p')
            if p_tag:
                description = p_tag.get_text(strip=True)

            # 提取编程语言
            language = ""
            lang_span = article.find('span', itemprop='programmingLanguage')
            if lang_span:
                language = lang_span.get_text(strip=True)

            # 提取stars和forks
            stars = 0
            forks = 0
            today_stars = 0

            for a_tag in article.find_all('a', href=True):
                href = a_tag.get('href', '')
                text = a_tag.get_text(strip=True)

                if '/stargazers' in href:
                    stars = self.parse_number(text)
                elif '/forks' in href:
                    forks = self.parse_number(text)

            # 提取今日新增星标
            # GitHub Trending显示今天的stars增长
            all_text = article.get_text()
            # 查找 "stars today" 或类似模式
            today_patterns = [
                r'(\d+[kmbKMB]?)\s*stars?\s*today',
                r'(\d+)\s+stars?\s+today',
                r'today[^\"\d]*(\d+)',
            ]
            for pattern in today_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    today_stars = self.parse_number(match.group(1))
                    if today_stars > 0:
                        break

            # 如果没有找到today_stars，尝试从其他元素中提取
            if today_stars == 0:
                # 尝试找到包含"today"的span
                for span in article.find_all('span'):
                    span_text = span.get_text(strip=True).lower()
                    if 'today' in span_text or 'star' in span_text:
                        # 提取数字
                        num_match = re.search(r'(\d+[kmbKMB]?)', span_text)
                        if num_match:
                            num = self.parse_number(num_match.group(1))
                            if num > 0 and num < stars:  # today stars should be less than total
                                today_stars = num
                                break

            return {
                "name": repo_name,
                "full_name": full_name,
                "description": description or "No description",
                "url": url,
                "stars": stars,
                "forks": forks,
                "today_stars": today_stars,
                "language": language or "Unknown",
                "owner": owner,
                "date": self.current_datetime,
                "created_at": None,
                "updated_at": None,
                "topics": [],
                "license": "",
                "open_issues": 0,
            }

        except Exception as e:
            print(f"  解析项目时出错: {e}")
            return None

    def get_readme_content(self, owner, repo_name):
        """获取GitHub仓库的README内容"""
        # 尝试多种README文件名
        readme_names = ['README.md', 'readme.md', 'README.md', 'README']

        headers = {"Accept": "application/vnd.github.v3.raw"}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        for readme_name in readme_names:
            # 尝试从raw.githubusercontent.com获取
            url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/{readme_name}"
            try:
                response = requests.get(url, headers=headers, timeout=10, proxies=self.proxies)
                if response.status_code == 200:
                    return response.text[:15000]  # 限制长度
            except:
                pass

            # 尝试master分支
            url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/{readme_name}"
            try:
                response = requests.get(url, headers=headers, timeout=10, proxies=self.proxies)
                if response.status_code == 200:
                    return response.text[:15000]
            except:
                pass

        # 如果直接获取失败，尝试使用GitHub API
        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # GitHub API返回base64编码的内容
                import base64
                data = response.json()
                content = base64.b64decode(data.get('content', '')).decode('utf-8', errors='ignore')
                return content[:15000]
        except:
            pass

        return None

    def analyze_repo_with_ai(self, owner, repo_name, description=""):
        """使用火山引擎豆包AI分析仓库README，生成中文描述"""
        # 检查缓存
        cache_key = f"{owner}/{repo_name}"
        if cache_key in self.analyzed_repos:
            return self.analyzed_repos[cache_key]

        if not self.volcano_api_key:
            print("  ⚠️  未设置VOLCANO_API_KEY环境变量，跳过AI分析")
            return None

        print(f"  🤖 正在AI分析 {cache_key}...")

        # 获取README内容
        readme = self.get_readme_content(owner, repo_name)

        if not readme:
            print(f"    ⚠️  无法获取README，跳过AI分析")
            return None

        # 构建AI提示词
        prompt = f"""请分析以下GitHub开源项目，用中文生成一段简洁的描述（200字以内）。

项目名称：{owner}/{repo_name}
原描述：{description}

README内容（截取）：
{readme[:8000]}

请按以下格式回答：
**是什么**：[项目是什么]
**有什么用**：[项目的核心功能和用途]
**怎么用**：[简单的使用方法或安装步骤]

要求：
1. 用简洁准确的中文
2. 突出项目的核心价值
3. 实用的使用建议
4. 总字数控制在200字以内
"""

        try:
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.volcano_api_key}"
            }

            payload = {
                "model": self.volcano_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }

            response = requests.post(
                self.volcano_api_url,
                headers=headers,
                json=payload,
                timeout=30,
                proxies=self.proxies_no_noproxy  # 国内服务不走代理
            )

            if response.status_code == 200:
                data = response.json()
                ai_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 清理内容
                ai_content = ai_content.strip()
                # 移除可能的markdown代码块标记
                if ai_content.startswith("```"):
                    ai_content = re.sub(r'^```[a-z]*\n', '', ai_content)
                    ai_content = re.sub(r'\n```$', '', ai_content)

                print(f"    ✓ AI分析完成")
                self.analyzed_repos[cache_key] = ai_content
                return ai_content
            else:
                print(f"    ✗ AI API错误: {response.status_code} - {response.text[:100]}")
                return None

        except Exception as e:
            print(f"    ✗ AI分析失败: {e}")
            return None

    def build_notion_properties(self, repo):
        """
        根据自动匹配的字段映射，构建Notion属性
        """
        properties = {}

        # 辅助函数：安全截断文本
        def truncate_text(text, max_length=2000):
            if not text:
                return ""
            text = str(text)
            return text[:max_length] if len(text) > max_length else text

        # 根据字段映射和属性类型构建数据
        for field_key, notion_prop_name in self.field_mapping.items():
            prop_type = self.db_properties[notion_prop_name].get("type")
            value = repo.get(field_key)

            # 跳过空值（除了date和today_stars，它们有默认值）
            if value is None and field_key not in ["date", "today_stars"]:
                continue

            # 根据Notion属性类型设置值
            if prop_type == "title":
                properties[notion_prop_name] = {
                    "title": [{"text": {"content": truncate_text(value, 2000)}}]
                }

            elif prop_type == "rich_text":
                # rich_text 可以存储字符串
                text_content = truncate_text(value, 2000) if value else ""
                properties[notion_prop_name] = {
                    "rich_text": [{"text": {"content": text_content}}]
                }

            elif prop_type == "text":
                properties[notion_prop_name] = {
                    "text": {"content": truncate_text(value, 2000)}
                }

            elif prop_type == "number" and isinstance(value, (int, float)):
                properties[notion_prop_name] = {"number": value}

            elif prop_type == "url":
                properties[notion_prop_name] = {"url": value}

            elif prop_type == "date":
                # 只有当值是日期格式时才使用date类型
                if isinstance(value, str) and len(value) >= 10:
                    properties[notion_prop_name] = {"date": {"start": value}}

            elif prop_type == "email" and "@" in str(value):
                properties[notion_prop_name] = {"email": str(value)}

            elif prop_type == "phone":
                properties[notion_prop_name] = {"phone_number": str(value)}

            elif prop_type == "checkbox":
                properties[notion_prop_name] = {"checkbox": bool(value)}

            elif prop_type == "multi_select" and field_key == "topics" and isinstance(value, list):
                # 处理topics标签
                options = self.db_properties[notion_prop_name].get("multi_select", {}).get("options", [])
                existing_options = {opt["name"]: opt["id"] for opt in options}

                selects = []
                for item in value[:10]:  # 最多10个标签
                    item_str = str(item)
                    if item_str in existing_options:
                        selects.append({"name": item_str})
                    else:
                        # 对于不存在的选项，Notion会忽略
                        selects.append({"name": item_str})

                if selects:
                    properties[notion_prop_name] = {"multi_select": selects}

            elif prop_type == "select" and value:
                # 处理单选
                value_str = truncate_text(value, 100)
                options = self.db_properties[notion_prop_name].get("select", {}).get("options", [])
                existing_options = {opt["name"]: opt["id"] for opt in options}

                if value_str in existing_options:
                    properties[notion_prop_name] = {"select": {"name": value_str}}

        return properties

    def add_to_notion(self, repo):
        """将单个仓库添加到Notion数据库"""
        url = "https://api.notion.com/v1/pages"

        properties = self.build_notion_properties(repo)

        if not properties:
            print(f"  ✗ {repo['full_name']}: 没有可写入的字段")
            return False

        # 必须指定parent（数据库ID）
        payload = {
            "parent": {"database_id": self.notion_database_id},
            "properties": properties
        }

        try:
            response = requests.post(
                url,
                headers=self.notion_headers,
                json=payload,
                proxies=self.proxies
            )

            if response.status_code == 200:
                today_display = f" | 今天+{repo['today_stars']}" if repo.get('today_stars') else ""
                print(f"  ✓ {repo['full_name'][:40]:40} ⭐ {repo['stars']}{today_display}")
                return True
            else:
                print(f"  ✗ {repo['full_name']}: {response.status_code} - {response.text[:100]}")
                return False

        except requests.RequestException as e:
            print(f"  ✗ 请求错误: {e}")
            return False

    def run(self):
        """执行主流程"""
        print("=" * 60)
        print(f"🚀 GitHub Trending → Notion + AI分析")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 1. 获取数据库结构
        print("\n[步骤 1/4] 获取Notion数据库结构...")
        if not self.get_database_schema():
            print("无法获取数据库结构，请检查token和数据库ID是否正确")
            return

        # 2. 自动匹配字段
        print("\n[步骤 2/4] 自动匹配数据库字段...")
        if not self.auto_match_fields():
            print("字段匹配失败，请检查数据库是否有必需的title字段")
            return

        # 3. 获取GitHub热门项目
        print("\n[步骤 3/4] 获取GitHub Trending热门项目...")
        trending_repos = self.get_trending_repos()

        if not trending_repos:
            print("没有获取到任何项目")
            return

        # 4. AI分析仓库（如果配置了API且数据库有对应字段）
        if "repo_detail" in self.field_mapping and self.volcano_api_key:
            print("\n[步骤 4/4] AI分析仓库README...")
            print("-" * 60)
            for repo in trending_repos:
                owner = repo.get("owner", "")
                name = repo.get("name", "")
                if owner and name:
                    ai_detail = self.analyze_repo_with_ai(owner, name, repo.get("description", ""))
                    if ai_detail:
                        repo["repo_detail"] = ai_detail
                time.sleep(0.5)  # 避免API限速
        else:
            if not self.volcano_api_key:
                print("\n[步骤 4/4] 跳过AI分析（未设置VOLCANO_API_KEY）")
            else:
                print("\n[步骤 4/4] 跳过AI分析（数据库无对应字段）")

        # 5. 写入Notion
        print(f"\n📝 写入Notion数据库:")
        print("-" * 60)
        success_count = 0
        for repo in trending_repos:
            if self.add_to_notion(repo):
                success_count += 1
            time.sleep(0.3)  # 避免API限速

        print("\n" + "=" * 60)
        print(f"✅ 完成! 成功添加 {success_count}/{len(trending_repos)} 个项目")
        print("=" * 60)


def main():
    bot = GitHubTrendingToNotion()
    bot.run()


if __name__ == "__main__":
    main()
