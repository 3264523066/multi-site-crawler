# 多站点通用爬虫框架

一个用 Python 编写的**可配置多网站爬虫框架**，通过声明式的站点配置即可爬取不同结构的网站，具备良好的通用性与可扩展性。

## 核心设计

- **`SiteConfig` 数据类**：每个目标站点用一份配置描述（名称、基础 URL、CSS 选择器映射、请求头、抓取延迟、编码），新增站点无需改动核心代码
- **`MultiSiteCrawler` 引擎**：统一调度多个站点的抓取任务
- **并发抓取**：基于 `ThreadPoolExecutor` 线程池并发执行，提升采集效率
- **反爬适配**：自定义 User-Agent / 请求头、随机化抓取延迟、Session 复用

## 功能特性

- CSS 选择器驱动的内容提取（基于 BeautifulSoup）
- 抓取结果导出为 **JSON / CSV**
- 完整日志体系：同时输出到控制台与 `crawler.log` 文件
- 超时与异常处理，单站点失败不影响整体任务

## 技术栈

`requests` · `BeautifulSoup4` · `concurrent.futures` · `dataclasses` · `logging`

## 快速开始

```bash
pip install requests beautifulsoup4
python multi_site_crawler.py
```

添加新站点只需构造一个 `SiteConfig`：

```python
config = SiteConfig(
    name="示例站点",
    base_url="https://example.com",
    selectors={"title": "h1", "content": ".article-body"},
    headers={},
    delay=1.5,
)
crawler.add_site_config(config)
```

## 免责声明

本项目仅供学习与技术研究使用，请遵守目标网站的 `robots.txt` 协议及相关法律法规，控制抓取频率，不得用于任何商业或侵权用途。
