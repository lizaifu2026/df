# coding: utf-8
# !/usr/bin/python


import base64
import hashlib
import json
import re
import time
import uuid
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base.spider import Spider


class Spider(Spider):
    BOOT_KEY = b"58928cae68092afc"
    BOOT_IV = b"e9d732a1edcdcc0a"

    DOMAIN_JS = "https://pub-77efc86e6df74acd99f2aa2227eedc2e.r2.dev/domain.js"
    DNS_DOMAIN = "yst.58yszx5.com"
    HOP_URLS = [
        "https://tt02.llshjf3.com/ys02.html",
        "https://tt02.ku93z.com/ys02.html",
        "https://tt02.job8629.com/ys02.html",
        "https://raw.githubusercontent.com/yixiujun886/viewerjs/refs/heads/main/src/domain.js",
    ]
    FALLBACK_ROOTS = [
        "https://a03.llshjf3.com",
        "https://sw02.job8629.com",
        "https://al02.llshjf3.com",
        "https://qe02.ku93z.com",
        "https://al01.ilovefhy.com",
        "https://a01.58sphapi.com",
    ]
    WEB_URL = "https://dfsfd.ynhongji.com/"
    APP_VERSION = "2.1.1"
    CHANNEL = ""
    PAGE_SIZE = 24

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

    TYPE_MAP = {
        "movie": "电影",
        "tv": "电视剧",
        "cartoon": "动漫",
        "variety": "综艺",
        "short": "短剧",
    }

    def getName(self):
        return "58影视"

    def init(self, extend):
        self.extend = extend or ""
        self.roots = []
        self.root_index = 0
        self.root = "https://a03.llshjf3.com"
        self.session = requests.Session()
        self.device_id = str(uuid.uuid4())
        self.secret = None
        self.config = {}
        self.image_domain = ""
        self._ready = False
        self.timeout = 20

        if isinstance(extend, str) and extend.strip():
            try:
                cfg = json.loads(extend)
                if isinstance(cfg, dict):
                    self.PAGE_SIZE = int(cfg.get("page_size") or cfg.get("pagesize") or self.PAGE_SIZE)
                    self.UA = cfg.get("ua") or cfg.get("user_agent") or self.UA
                    if cfg.get("root"):
                        self.root = str(cfg.get("root")).rstrip("/")
                        self.roots = [self.root]
                    if cfg.get("channel"):
                        self.CHANNEL = str(cfg.get("channel"))
            except Exception:
                pass

        self._reset_session()

    def isVideoFormat(self, url):
        return None

    def manualVideoCheck(self):
        return None

    def _reset_session(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self.WEB_URL.rstrip("/"),
            "Referer": self.WEB_URL,
            "X-Device-UUID": self.device_id,
        })

    def _aes_cbc_decrypt_b64(self, cipher_text):
        raw = base64.b64decode(str(cipher_text).strip())
        dec = AES.new(self.BOOT_KEY, AES.MODE_CBC, self.BOOT_IV).decrypt(raw)
        return unpad(dec, AES.block_size).decode("utf-8")

    def _aes_ecb_decrypt_b64_with_secret(self, cipher_text):
        key = hashlib.sha256(str(self.secret).encode("utf-8")).digest()
        raw = base64.b64decode(str(cipher_text).strip())
        dec = AES.new(key, AES.MODE_ECB).decrypt(raw)
        return unpad(dec, AES.block_size).decode("utf-8")

    def _add_root(self, roots, url):
        url = str(url or "").strip().strip('"').rstrip("/")
        if not url or not url.startswith(("http://", "https://")):
            return
        if url not in roots:
            roots.append(url)

    def _parse_root_text(self, text):
        text = str(text or "").strip()
        if not text:
            return []
        plain = text
        if "http" not in plain:
            try:
                plain = self._aes_cbc_decrypt_b64(plain)
            except Exception:
                plain = text
        roots = []
        for item in re.split(r"[,\n\r\t ]+", plain):
            self._add_root(roots, item)
        return roots

    def _load_dns_roots(self):
        roots = []
        doh_urls = [
            "https://dns.alidns.com/resolve",
            "https://sm2.doh.pub/dns-query",
            "https://223.5.5.5/resolve",
        ]
        for doh in doh_urls:
            try:
                r = requests.get(doh, params={"name": self.DNS_DOMAIN, "type": "16"}, headers={"User-Agent": self.UA}, timeout=8)
                data = r.json()
                for ans in data.get("Answer") or []:
                    if int(ans.get("type") or 0) != 16:
                        continue
                    val = str(ans.get("data") or "").strip().strip('"')
                    for root in self._parse_root_text(val):
                        self._add_root(roots, root)
                if roots:
                    break
            except Exception:
                continue
        return roots

    def _load_hop_roots(self):
        roots = []
        for url in self.HOP_URLS:
            try:
                r = requests.get(url, headers={"User-Agent": self.UA, "Referer": self.WEB_URL}, timeout=8)
                for root in self._parse_root_text(r.text):
                    self._add_root(roots, root)
            except Exception:
                continue
        return roots

    def _load_roots(self):
        if self.roots:
            return self.roots
        roots = []

       
        for root in self._load_dns_roots() + self._load_hop_roots():
            self._add_root(roots, root)

       
        try:
            r = requests.get(self.DOMAIN_JS, headers={"User-Agent": self.UA, "Referer": self.WEB_URL}, timeout=8)
            for root in self._parse_root_text(r.text):
                self._add_root(roots, root)
        except Exception:
            pass

        if self.root:
            self._add_root(roots, self.root)
        for root in self.FALLBACK_ROOTS:
            self._add_root(roots, root)
        self.roots = roots or list(self.FALLBACK_ROOTS)
        return self.roots

    def _register(self):
        payload = {
            "app_version": self.APP_VERSION,
            "device_id": self.device_id,
            "model": "Web",
            "os_version": "0",
            "platform": "Web",
            "source_domain": urlparse(self.WEB_URL).netloc,
            "channel": self.CHANNEL,
        }
        data = self._raw_request("POST", "/v1/client/auth/visitor/register", json=payload, skip_boot=True)
        if isinstance(data, dict):
            self.secret = data.get("secret") or self.secret
            if data.get("uuid"):
                self.device_id = data.get("uuid")
                self.session.headers.update({"X-Device-UUID": self.device_id})
        return data

    def _ensure(self):
        if self._ready:
            return
        roots = self._load_roots()
        last_err = None
        for idx, root in enumerate(roots):
            try:
                self.root_index = idx
                self.root = root.rstrip("/")
                self.device_id = str(uuid.uuid4())
                self.secret = None
                self._reset_session()
                self._register()
                cfg = self._raw_request("GET", "/v1/client/app/config", skip_boot=True)
                if isinstance(cfg, dict):
                    self.config = cfg
                    self.image_domain = str(cfg.get("image_domain") or cfg.get("imageDomain") or "").rstrip("/")
                self._ready = True
                return
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err

    def _raw_request(self, method, path, params=None, json=None, skip_boot=False):
        url = path if str(path).startswith("http") else self.root.rstrip("/") + path
        r = self.session.request(method, url, params=params, json=json, timeout=self.timeout)
        text = (r.text or "").strip()
        if self.secret and text and not text.startswith("{") and not text.startswith("["):
            try:
                text = self._aes_ecb_decrypt_b64_with_secret(text)
            except Exception:
                pass
        if not text:
            return {}
        data = json_loads(text)
        if isinstance(data, dict) and data.get("code") == 0:
            return data.get("data")
        return data

    def _request(self, method, path, params=None, json=None):
        self._ensure()
        try:
            return self._raw_request(method, path, params=params, json=json)
        except Exception:
            self._ready = False
            self._ensure()
            return self._raw_request(method, path, params=params, json=json)

    def _join_url(self, domain, path):
        path = str(path or "").strip()
        domain = str(domain or "").strip().rstrip("/")
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if domain:
            return domain + (path if path.startswith("/") else "/" + path)
        return urljoin(self.WEB_URL, path)

    def _play_headers(self, url=""):
        host = ""
        try:
            from urllib.parse import urlparse
            u = urlparse(url or self.WEB_URL)
            host = u.scheme + "://" + u.netloc + "/" if u.scheme and u.netloc else self.WEB_URL
        except Exception:
            host = self.WEB_URL
        return {
            "User-Agent": self.UA,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Referer": self.WEB_URL,
            "Origin": self.WEB_URL.rstrip("/"),
        }

    def _proxy_url(self, url, typ="m3u8"):
        url = str(url or "").strip()
        if not url:
            return ""
        try:
            return self.getProxyUrl() + "&type=" + typ + "&url=" + quote(url, safe="")
        except Exception:
            return url

    def _cover(self, vod):
        imgs = vod.get("coverImages") or vod.get("cover_images") or vod.get("screenshot_images") or []
        if isinstance(imgs, str):
            return self._join_url(self.image_domain, imgs)
        if not isinstance(imgs, list) or not imgs:
            return ""
        chosen = None
        for img in imgs:
            if isinstance(img, dict) and img.get("type") == "vertical":
                chosen = img
                break
        if chosen is None:
            chosen = imgs[0]
        url = chosen.get("url") if isinstance(chosen, dict) else str(chosen)
        return self._join_url(self.image_domain, url)

    def _names(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            out = []
            for x in value:
                if isinstance(x, dict):
                    out.append(str(x.get("name") or x.get("title") or ""))
                else:
                    out.append(str(x))
            return ",".join([x for x in out if x])
        if isinstance(value, dict):
            return str(value.get("name") or value.get("title") or "")
        return str(value)

    def _tag_names(self, tags):
        if not tags:
            return ""
        if isinstance(tags, list):
            return ",".join([str(x.get("name") if isinstance(x, dict) else x) for x in tags if x])
        return str(tags)

    def _vod_item(self, vod):
        vid = vod.get("id") or vod.get("video_id") or ""
        typ = vod.get("type") or ""
        remarks = vod.get("state") or vod.get("remark") or vod.get("premiumBlurb") or vod.get("premium_blurb") or ""
        if not remarks:
            ep = vod.get("episodes") or 0
            serial = vod.get("serial") or 0
            if ep:
                remarks = "全%s集" % ep if serial >= ep else "更新至%s/%s集" % (serial, ep)
        return {
            "vod_id": "%s|%s" % (vid, typ) if typ else str(vid),
            "vod_name": str(vod.get("title") or vod.get("vod_name") or "").strip(),
            "vod_pic": self._cover(vod),
            "vod_remarks": str(remarks or ""),
        }

    def _home_videos(self):
       
        payloads = [
            {"page": 1, "size": self.PAGE_SIZE},
            {"page": 1, "page_size": self.PAGE_SIZE},
            {"page": 1, "pageSize": self.PAGE_SIZE},
        ]
        for payload in payloads:
            try:
                data = self._request("POST", "/v1/client/filter/video", json=payload)
                videos = data.get("list", []) if isinstance(data, dict) else []
                vods = [self._vod_item(x) for x in videos if isinstance(x, dict)]
                if vods:
                    return vods
            except Exception:
                continue
        
        try:
            return self.categoryContent("movie", "1", False, {}).get("list", [])
        except Exception:
            return []

    def homeContent(self, filter):
        classes = [{"type_id": k, "type_name": v} for k, v in self.TYPE_MAP.items()]
        result = {"class": classes, "list": self._home_videos()}
        if filter:
            result["filters"] = {k: [] for k in self.TYPE_MAP.keys()}
        return result

    def homeVideoContent(self):
        return {"list": self._home_videos()}

    def categoryContent(self, cid, pg, filter, ext):
        try:
            page = int(pg)
        except Exception:
            page = 1
        payload = {"page": page, "size": self.PAGE_SIZE}
        if cid and cid != "all":
            payload["type"] = cid
        if isinstance(ext, dict):
            for k, v in ext.items():
                if v not in (None, "", [], {}):
                    payload[k] = v
        data = self._request("POST", "/v1/client/filter/video", json=payload)
        total = data.get("total", 0) if isinstance(data, dict) else 0
        videos = data.get("list", []) if isinstance(data, dict) else []
        return {
            "list": [self._vod_item(x) for x in videos],
            "page": page,
            "pagecount": max(1, int((int(total or 0) + self.PAGE_SIZE - 1) / self.PAGE_SIZE)) if total else 999,
            "limit": self.PAGE_SIZE,
            "total": int(total or 999999),
        }

    def detailContent(self, ids):
        raw_id = str(ids[0]) if ids else ""
        vid = raw_id.split("|")[0]
        data = self._request("GET", "/v1/client/video/video/video_detail", params={"video_id": vid})
        if not isinstance(data, dict):
            return {"list": []}

        play_urls = []
        direct_urls = []
        eps = data.get("episode_list") or []
        if isinstance(eps, list):
            eps = sorted(eps, key=lambda x: int(x.get("episode") or 0) if isinstance(x, dict) else 0)
        for ep in eps:
            if not isinstance(ep, dict):
                continue
            sources = ep.get("sources") or []
            src = None
            for s in sources:
                if isinstance(s, dict) and s.get("play_url"):
                    src = s
                    break
            if not src:
                continue
            title = str(ep.get("title") or ("第%s集" % (ep.get("episode") or len(play_urls) + 1))).strip()
            safe_title = title.replace("#", " ").replace("$", " ")
            url = self._join_url(src.get("domain"), src.get("play_url"))
            if url:
                
                proxied = self._proxy_url(url, "m3u8")
                if proxied and proxied != url:
                    play_urls.append(safe_title + "$" + proxied)
                    direct_urls.append(safe_title + "$" + url)
                else:
                    play_urls.append(safe_title + "$" + url)

        persons = data.get("persons") or []
        actor = ""
        director = ""
        if isinstance(persons, list):
            actors, directors = [], []
            for p in persons:
                if not isinstance(p, dict):
                    continue
                name = p.get("name") or p.get("person_name") or p.get("title")
                role = str(p.get("type") or p.get("role") or "")
                if not name:
                    continue
                if "导演" in role or "director" in role.lower():
                    directors.append(str(name))
                else:
                    actors.append(str(name))
            actor = ",".join(actors)
            director = ",".join(directors)

        vod = {
            "vod_id": raw_id,
            "vod_name": str(data.get("title") or ""),
            "vod_pic": self._cover(data),
            "type_name": self.TYPE_MAP.get(str(data.get("type") or ""), str(data.get("type") or "")),
            "vod_year": str(data.get("year") or data.get("years") or ""),
            "vod_area": self._names(data.get("areas") or data.get("area")),
            "vod_lang": self._names(data.get("language")),
            "vod_actor": actor or self._names(data.get("actors")),
            "vod_director": director or self._names(data.get("director")),
            "vod_remarks": str(data.get("state") or "全%s集" % data.get("episodes") if data.get("episodes") else ""),
            "vod_content": str(data.get("content") or data.get("blurb") or data.get("premium_blurb") or ""),
            "vod_play_from": "58影视代理$$$58影视直连" if direct_urls else "58影视",
            "vod_play_url": "#".join(play_urls) + ("$$$" + "#".join(direct_urls) if direct_urls else ""),
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()
        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": self._play_headers(url),
        }

    def searchContentPage(self, key, quick, page):
        try:
            pg = int(page)
        except Exception:
            pg = 1
        keyword = str(key or "").strip()

       
        try:
            params = {"keyword": keyword, "page": pg, "size": self.PAGE_SIZE}
            data = self._request("GET", "/v1/client/search/video", params=params)
            if isinstance(data, dict):
                items = data.get("list") or []
                total = int(data.get("total") or len(items) or 0)
                return {
                    "list": [self._vod_item(x) for x in items if isinstance(x, dict)],
                    "page": pg,
                    "pagecount": max(1, int((total + self.PAGE_SIZE - 1) / self.PAGE_SIZE)) if total else 1,
                    "limit": self.PAGE_SIZE,
                    "total": total,
                }
        except Exception:
            pass

        
        kw = keyword.lower()
        videos = []
        seen = set()
        for typ in self.TYPE_MAP.keys():
            try:
                data = self._request("POST", "/v1/client/filter/video", json={"page": pg, "size": self.PAGE_SIZE, "type": typ})
                items = data.get("list", []) if isinstance(data, dict) else []
                for item in items:
                    name = str(item.get("title") or "")
                    sub = self._names(item.get("subtitle"))
                    if (not kw) or kw in name.lower() or kw in sub.lower():
                        vid = item.get("id")
                        if vid in seen:
                            continue
                        seen.add(vid)
                        videos.append(self._vod_item(item))
            except Exception:
                continue
        return {"list": videos, "page": pg, "pagecount": 1 if videos else 0, "limit": self.PAGE_SIZE, "total": len(videos)}

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def localProxy(self, params):
        try:
            typ = params.get("type") if isinstance(params, dict) else ""
            if typ == "m3u8":
                return self.proxyM3u8(params)
            if typ in ("media", "ts", "key"):
                return self.proxyMedia(params)
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8"), {}]
        return None

    def proxyM3u8(self, params):
        url = unquote(params.get("url", ""))
        r = requests.get(url, headers=self._play_headers(url), timeout=self.timeout, allow_redirects=True)
        r.encoding = "utf-8"
        base = r.url or url
        text = r.text or ""

        def repl_uri(m):
            raw = m.group(1)
            abs_url = urljoin(base, raw)
            ptype = "m3u8" if ".m3u8" in abs_url.lower() else "media"
            return 'URI="' + self._proxy_url(abs_url, ptype) + '"'

        out = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                out.append(line)
                continue
            if s.startswith("#"):
                if "URI=" in s:
                    s = re.sub(r'URI="([^"]+)"', repl_uri, s)
                out.append(s)
                continue
            abs_url = urljoin(base, s)
            ptype = "m3u8" if ".m3u8" in abs_url.lower() else "media"
            out.append(self._proxy_url(abs_url, ptype))
        body = ("\n".join(out) + "\n").encode("utf-8")
        return [200, "application/vnd.apple.mpegurl", body, {"Access-Control-Allow-Origin": "*"}]

    def proxyMedia(self, params):
        url = unquote(params.get("url", ""))
        r = requests.get(url, headers=self._play_headers(url), timeout=self.timeout, stream=False, allow_redirects=True)
        ctype = r.headers.get("Content-Type") or "application/octet-stream"
        return [200, ctype, r.content, {"Access-Control-Allow-Origin": "*"}]


def json_loads(text):
    try:
        return json.loads(text)
    except Exception:
        return text
