# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import urllib.parse
import re
import requests
from lxml import etree
from urllib.parse import urljoin
import json
import base64
import time

class Spider(Spider):

    def getName(self):
        return "侠盗影院"

    def init(self, extend=""):
        self.host = "http://xidim.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host,
        }
        self.log(f"爬虫初始化: {self.host}")

    def homeContent(self, filter):
        classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
            {'type_id': '30', 'type_name': '爽文短剧'},
            {'type_id': '36', 'type_name': '伦理片'},
        ]
        return {
            'class': classes,
            'list': self._fetch_videos(self.host)
        }

    def homeVideoContent(self):
        return {'list': self._fetch_videos(self.host)}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/type/{tid}.html"
        if str(pg) != '1':
            url = f"{self.host}/type/{tid}-{pg}.html"
        videos = self._fetch_videos(url)
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 999,
            'limit': 20,
            'total': 9999
        }

    def searchContent(self, key, quick, pg="1"):
        wd = urllib.parse.quote(key)
        url = f"{self.host}/search/{wd}----------{pg}---.html"
        videos = self._fetch_videos(url)
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 10,
            'limit': 20,
            'total': 100
        }

    def detailContent(self, ids):
        try:
            url = ids[0]
            rsp = self.fetch(url)
            if not rsp or rsp.status_code != 200:
                return {'list': []}

            html = etree.HTML(rsp.text)
            if html is None:
                return {'list': []}

            # 标题
            title = ''.join(html.xpath('//h1[@class="title"]/text()')).strip()
            if not title:
                title = ''.join(html.xpath('//title/text()')).strip()
                title = re.sub(r'《|》', '', title)
                title = re.split(r'在线观看| - ', title)[0].strip()

            # 海报
            pic = ''.join(html.xpath('//div[contains(@class,"macplus-contentthumb")]//img/@data-original')).strip()
            if not pic:
                pic = ''.join(html.xpath('//div[contains(@class,"macplus-contentthumb")]//img/@src')).strip()
            if pic and not pic.startswith('http'):
                pic = urljoin(self.host, pic)

            # 简介
            desc = ''.join(html.xpath('//meta[@name="description"]/@content')).strip()
            if not desc:
                desc = ''.join(html.xpath('//span[@id="cText"]//text()')).strip()
                desc = re.sub(r'\s+', ' ', desc)

            # 播放线路和列表
            play_from = []
            play_urls = []

            # 线路名称
            tab_links = html.xpath('//ul[@id="playTab"]/li/a')
            tabs = [self.clean_text(a.xpath('.//text()')) for a in tab_links if self.clean_text(a.xpath('.//text()'))]
            # 播放列表容器
            playlist_uls = html.xpath('//ul[contains(@class,"macplus-content__playlist")]')

            for idx, ul in enumerate(playlist_uls):
                from_name = tabs[idx] if idx < len(tabs) else f'线路{idx+1}'
                urls = []
                for a in ul.xpath('.//li/a'):
                    name = self.clean_text(a.xpath('.//text()'))
                    href = a.get('href', '').strip()
                    if not href:
                        continue
                    full_url = urljoin(self.host, href)
                    urls.append(f"{name}${full_url}")
                if urls:
                    play_from.append(from_name)
                    play_urls.append('#'.join(urls))

            return {
                'list': [{
                    'vod_id': url,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_content': desc,
                    'vod_play_from': '$$$'.join(play_from),
                    'vod_play_url': '$$$'.join(play_urls)
                }]
            }
        except Exception as e:
            self.log(f"detailContent error: {e}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            rsp = self.fetch(id)
            if not rsp or rsp.status_code != 200:
                return {'parse': 1, 'url': id}

            html = rsp.text

            # 原加密播放地址解析
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
            if m:
                data = json.loads(m.group(1))
                play_url = data.get('url', '')
                encrypt = str(data.get('encrypt', '0'))

                if encrypt == '1':
                    play_url = urllib.parse.unquote(play_url)
                elif encrypt == '2':
                    play_url = urllib.parse.unquote(play_url)
                    try:
                        play_url = base64.b64decode(play_url).decode('utf-8')
                    except:
                        pass

                if play_url.startswith('//'):
                    play_url = 'https:' + play_url
                elif play_url.startswith('/'):
                    play_url = urljoin(self.host, play_url)

                if '.m3u8' in play_url or '.mp4' in play_url:
                    return {'parse': 0, 'playUrl': '', 'url': play_url}
                else:
                    return {'parse': 1, 'url': play_url}

            # 直接搜索视频地址
            m2 = re.search(r'(https?://[^\s\'\"]+?\.m3u8[^\s\'\"]*)', html)
            if m2:
                return {'parse': 0, 'playUrl': '', 'url': m2.group(1)}
            m3 = re.search(r'(https?://[^\s\'\"]+?\.mp4[^\s\'\"]*)', html)
            if m3:
                return {'parse': 0, 'playUrl': '', 'url': m3.group(1)}

            return {'parse': 1, 'url': id}
        except Exception as e:
            self.log(f"playerContent error: {e}")
            return {'parse': 1, 'url': id}

    def _fetch_videos(self, url):
        try:
            # 重试
            for attempt in range(3):
                rsp = self.fetch(url)
                if rsp and rsp.status_code == 200:
                    break
                time.sleep(1)
            else:
                self.log(f"请求失败: {url}")
                return []

            # 编码处理
            html_content = rsp.text
            if not html_content.strip():
                for encoding in ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']:
                    try:
                        html_content = rsp.content.decode(encoding)
                        if html_content.strip():
                            break
                    except:
                        continue

            html = etree.HTML(html_content)
            if html is None:
                self.log("HTML解析失败")
                return []

            videos = []
            seen = set()

            # 根据分类页实际结构选择视频项
            items = html.xpath('//li[contains(@class,"col-md-7") and contains(@class,"col-sm-4")]')
            if not items:
                # 尝试首页结构（可能不同，但暂用同一种）
                items = html.xpath('//div[contains(@class,"macplus-vodlist__bag")]')

            self.log(f"找到 {len(items)} 个候选视频项")

            for item in items:
                # 提取链接和标题
                a_thumb = item.xpath('.//a[contains(@class,"macplus-vodlist__thumb")]')
                if not a_thumb:
                    # 如果没有thumb，尝试找任意a标签
                    a_thumb = item.xpath('.//a')
                if not a_thumb:
                    continue
                a = a_thumb[0]
                href = a.get('href', '').strip()
                if not href or href.startswith('javascript:'):
                    continue

                full_url = urljoin(self.host, href)
                if full_url in seen:
                    continue
                seen.add(full_url)

                # 标题优先使用title属性，否则取h4中的文本
                title = a.get('title', '').strip()
                if not title:
                    h4_a = item.xpath('.//h4[contains(@class,"title")]//a')
                    if h4_a:
                        title = h4_a[0].get('title', '').strip() or self.clean_text(h4_a[0].xpath('.//text()'))
                if not title:
                    title = self.clean_text(a.xpath('.//text()'))
                if not title:
                    continue

                # 图片
                pic = a.get('data-original', '').strip()
                if not pic:
                    pic = a.get('src', '').strip()
                if pic and not pic.startswith('http'):
                    pic = urljoin(self.host, pic)

                # 备注
                remark = ''
                span_pic = item.xpath('.//span[contains(@class,"pic-text")]')
                if span_pic:
                    remark = self.clean_text(span_pic[0].xpath('.//text()'))

                videos.append({
                    'vod_id': full_url,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark,
                    'vod_year': ''
                })

            self.log(f"最终解析到 {len(videos)} 个视频")
            if not videos:
                # 输出调试信息
                sample = html_content[:500]
                self.log(f"页面片段: {sample}")
            return videos
        except Exception as e:
            self.log(f"_fetch_videos error: {e}")
            return []

    def clean_text(self, text_list):
        """清理文本，去除空白和换行"""
        if not text_list:
            return ''
        return ' '.join(''.join(text_list).split()).strip()

    def log(self, msg):
        print(f"[侠盗影院] {msg}")

    def fetch(self, url):
        try:
            session = requests.Session()
            session.headers.update(self.headers)
            response = session.get(url, timeout=10, verify=False)
            return response
        except Exception as e:
            self.log(f"fetch error: {e}")
            return None