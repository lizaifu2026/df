from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
from binascii import Error as BinasciiError
import sys
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        '''
        example:
        {
            "key": "py_appV2",
            "name": "xxx",
            "type": 3,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1,
            "api": "./py/影探.py",
            "ext": "http://cmsyt.lyyytv.cn"
        }
        
        '''

        self.host=extend
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'okhttp/4.12.0',
    }

    def homeContent(self, filter):
        data = self.fetch(f"{self.host}/api.php/app/nav?token=",headers=self.headers).json()
        keys = ["class", "area", "lang", "year", "letter", "by", "sort"]
        filters = {}
        classes = []
        for item in data['list']:
            has_non_empty_field = False
            jsontype_extend = item["type_extend"]
            classes.append({"type_name": item["type_name"], "type_id": item["type_id"]})
            for key in keys:
                if key in jsontype_extend and jsontype_extend[key].strip() != "":
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
            for dkey in jsontype_extend:
                if dkey in keys and jsontype_extend[dkey].strip() != "":
                    values = jsontype_extend[dkey].split(",")
                    value_array = [{"n": value.strip(), "v": value.strip()} for value in values if
                                   value.strip() != ""]
                    filters[str(item["type_id"])].append({"key": dkey, "name": dkey, "value": value_array})
        result = {}
        result["class"] = classes
        result["filters"] = filters
        return result

    def homeVideoContent(self):
        data=self.fetch(f"{self.host}/api.php/app/index_video?token=",headers=self.headers).json()
        videos=[]
        for item in data['list']:videos.extend(item['vlist'])
        return {'list':videos}

    def categoryContent(self, tid, pg, filter, extend):
        params = {'tid':tid,'class':extend.get('class',''),'area':extend.get('area',''),'lang':extend.get('lang',''),'year':extend.get('year',''),'limit':'18','pg':pg}
        data=self.fetch(f"{self.host}/api.php/app/video",params=params,headers=self.headers).json()
        return data

    def ui6_lvdou(self, text ,cmskey = 'z0afJ9wfCMDuLwDMJqFHwFGmaxCzC5zM'):
        key = cmskey[:16].encode("utf-8")
        iv = cmskey[-16:].encode("utf-8")

        original_text = text
        url_prefix = "lvdou+"
        if original_text.startswith(url_prefix):
            ciphertext_b64 = original_text[len(url_prefix):]
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                ct_bytes = base64.b64decode(ciphertext_b64)
                pt_bytes = cipher.decrypt(ct_bytes)
                pt = unpad(pt_bytes, AES.block_size)
                decrypted_text = pt.decode('utf-8')
                return decrypted_text
            except (BinasciiError, ValueError, UnicodeDecodeError):
                # 捕获Base64解码错误、填充错误或解码失败异常
                return original_text
        else:
            return original_text

    def detailContent(self, ids):
        data=self.fetch(f"{self.host}/api.php/app/video_detail?id={ids[0]}",headers=self.headers).json()
        new_vod_url_with_player = (self.process_data(data['data']['vod_url_with_player']))
        data['data']['vod_url_with_player'] = new_vod_url_with_player
        #print(self.ui6_lvdou('lvdou++n8/tmDZnKQlM6vQDsFYfufbDlNRktSi6ze5FQENoDj0IMBDOeo5j7VjZimZmOWxCvk1eRlIGqC+ppyHm8QkOQ=='))

        return  {'list':[data['data']]}

    def searchContent(self, key, quick, pg="1"):
        data=self.fetch(f"{self.host}/api.php/app/search?text={key}&pg={pg}",headers=self.headers).json()
        videos=data['list']
        for item in data['list']:
            item.pop('type', None)
        return {'list':videos,'page':pg}

    def playerContent(self, flag, id, vipFlags):
        return  {'jx':1,'playUrl':'','parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        pass

    def process_data(self,data):
        processed = []
        for item in data:
            # 创建新字典以避免修改原始数据
            new_item = item.copy()
            url = new_item.get('url', '')
            if url:
                parts = url.split('#')
                new_parts = []
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    # 分割名称和URL部分
                    split_part = part.split('$', 1)
                    if len(split_part) == 2:
                        name, url_part = split_part
                        decoded_url = self.ui6_lvdou(url_part)  # 假设url_decode已定义
                        new_part = f"{name}${decoded_url}"
                    else:
                        # 如果无法分割，保留原样（根据需求可能需要不同处理）
                        new_part = part
                    new_parts.append(new_part)
                # 更新处理后的url
                new_item['url'] = '#'.join(new_parts)
            processed.append(new_item)
        return processed
