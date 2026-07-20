#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多网站爬虫框架
支持爬取多个不同网站的内容，具有通用性和可扩展性
"""

import requests
import time
import json
import csv
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Any, Optional
import random
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SiteConfig:
    """网站配置类"""
    name: str
    base_url: str
    selectors: Dict[str, str]  # CSS选择器映射
    headers: Dict[str, str]
    delay: float = 1.0
    encoding: str = 'utf-8'
    use_session: bool = True

class MultiSiteCrawler:
    """多网站爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        
        # 通用请求头
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def add_site_config(self, config: SiteConfig):
        """添加网站配置"""
        if not hasattr(self, 'site_configs'):
            self.site_configs = []
        self.site_configs.append(config)
        logger.info(f"添加网站配置: {config.name}")
    
    def get_page_content(self, url: str, headers: Dict[str, str] = None, encoding: str = 'utf-8') -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            # 合并请求头
            request_headers = self.default_headers.copy()
            if headers:
                request_headers.update(headers)
            
            response = self.session.get(url, headers=request_headers, timeout=30)
            response.raise_for_status()
            
            # 设置编码
            if encoding:
                response.encoding = encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info(f"成功获取页面: {url}")
            return soup
            
        except requests.RequestException as e:
            logger.error(f"请求失败 {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"解析页面失败 {url}: {e}")
            return None
    
    def extract_data(self, soup: BeautifulSoup, selectors: Dict[str, str]) -> Dict[str, Any]:
        """根据选择器提取数据"""
        data = {}
        
        for field, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        # 单个元素
                        element = elements[0]
                        if element.name in ['img']:
                            data[field] = element.get('src', '')
                        elif element.name in ['a']:
                            data[field] = {
                                'text': element.get_text(strip=True),
                                'href': element.get('href', '')
                            }
                        else:
                            data[field] = element.get_text(strip=True)
                    else:
                        # 多个元素
                        data[field] = []
                        for element in elements:
                            if element.name in ['img']:
                                data[field].append(element.get('src', ''))
                            elif element.name in ['a']:
                                data[field].append({
                                    'text': element.get_text(strip=True),
                                    'href': element.get('href', '')
                                })
                            else:
                                data[field].append(element.get_text(strip=True))
                else:
                    data[field] = None
                    
            except Exception as e:
                logger.error(f"提取字段 {field} 失败: {e}")
                data[field] = None
        
        return data
    
    def crawl_site(self, config: SiteConfig, urls: List[str]) -> List[Dict[str, Any]]:
        """爬取单个网站"""
        site_results = []
        
        logger.info(f"开始爬取网站: {config.name}")
        
        for url in urls:
            try:
                # 获取页面内容
                soup = self.get_page_content(url, config.headers, config.encoding)
                if not soup:
                    continue
                
                # 提取数据
                data = self.extract_data(soup, config.selectors)
                data['source_url'] = url
                data['site_name'] = config.name
                data['crawl_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                site_results.append(data)
                logger.info(f"成功爬取: {url}")
                
                # 延时
                if config.delay > 0:
                    time.sleep(config.delay + random.uniform(0, 0.5))
                    
            except Exception as e:
                logger.error(f"爬取URL失败 {url}: {e}")
                continue
        
        logger.info(f"网站 {config.name} 爬取完成，共获取 {len(site_results)} 条数据")
        return site_results
    
    def crawl_all_sites(self, site_urls: Dict[str, List[str]], max_workers: int = 3) -> List[Dict[str, Any]]:
        """并发爬取所有网站"""
        all_results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_site = {}
            
            # 提交爬取任务
            for config in self.site_configs:
                if config.name in site_urls:
                    urls = site_urls[config.name]
                    future = executor.submit(self.crawl_site, config, urls)
                    future_to_site[future] = config.name
            
            # 收集结果
            for future in as_completed(future_to_site):
                site_name = future_to_site[future]
                try:
                    site_results = future.result()
                    all_results.extend(site_results)
                except Exception as e:
                    logger.error(f"网站 {site_name} 爬取失败: {e}")
        
        self.results = all_results
        logger.info(f"所有网站爬取完成，共获取 {len(all_results)} 条数据")
        return all_results
    
    def save_to_json(self, filename: str = 'crawler_results.json'):
        """保存结果到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"结果已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def save_to_csv(self, filename: str = 'crawler_results.csv'):
        """保存结果到CSV文件"""
        if not self.results:
            logger.warning("没有数据可保存")
            return
        
        try:
            # 获取所有字段名
            all_fields = set()
            for result in self.results:
                all_fields.update(result.keys())
            
            fieldnames = sorted(list(all_fields))
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.results:
                    # 处理复杂数据类型
                    row = {}
                    for field in fieldnames:
                        value = result.get(field, '')
                        if isinstance(value, (dict, list)):
                            row[field] = json.dumps(value, ensure_ascii=False)
                        else:
                            row[field] = value
                    writer.writerow(row)
            
            logger.info(f"结果已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")

# 示例配置
def create_example_configs():
    """创建示例网站配置"""
    configs = []
    
    # 示例网站1配置
    config1 = SiteConfig(
        name="示例网站1",
        base_url="https://example1.com",
        selectors={
            "title": "h1",
            "content": ".content",
            "author": ".author",
            "date": ".date",
            "tags": ".tag"
        },
        headers={
            "Referer": "https://example1.com"
        },
        delay=1.0
    )
    configs.append(config1)
    
    # 示例网站2配置
    config2 = SiteConfig(
        name="示例网站2",
        base_url="https://example2.com",
        selectors={
            "title": ".title",
            "description": ".desc",
            "price": ".price",
            "image": "img.product-img",
            "rating": ".rating"
        },
        headers={
            "Referer": "https://example2.com"
        },
        delay=1.5
    )
    configs.append(config2)
    
    return configs

if __name__ == "__main__":
    # 创建爬虫实例
    crawler = MultiSiteCrawler()
    
    # 添加网站配置
    configs = create_example_configs()
    for config in configs:
        crawler.add_site_config(config)
    
    # 定义要爬取的URL
    site_urls = {
        "示例网站1": [
            "https://example1.com/page1",
            "https://example1.com/page2"
        ],
        "示例网站2": [
            "https://example2.com/product1",
            "https://example2.com/product2"
        ]
    }
    
    # 开始爬取
    results = crawler.crawl_all_sites(site_urls)
    
    # 保存结果
    crawler.save_to_json()
    crawler.save_to_csv()
    
    print(f"爬取完成！共获取 {len(results)} 条数据")
