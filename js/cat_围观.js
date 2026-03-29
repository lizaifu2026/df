/*
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '围观短剧',
  lang: 'cat'
})
*/


let siteName = '围观短剧';
let siteKey = '';
let siteType = 0;

let UA = "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36";

// ==================== URL配置集中管理 ====================
let rule = {
    host: 'https://api.drama.9ddm.com',
    tagsUrl: '/drama/home/shortVideoTags',
    searchUrl: '/drama/home/search?version_code=1500',
    detailUrl: '/drama/home/shortVideoDetail?version_code=1500'
};

function init(cfg) {
    siteName = (cfg.skey?.split('_')[1] || cfg.skey) || (cfg.key?.split('_')[1] || cfg.key) || '未知';
    siteKey = cfg.skey;
    siteType = cfg.stype;
}


//分类
async function home(filter, param) {
    let classes = [];
    let filters = {};
    
    const response = await request(`${rule.host}${rule.tagsUrl}`, {
        headers: {
            'User-Agent': UA,
        }
    });

    const data = JSON.parse(response);
    
    if (data && data.code === 200) {
        // 分类：男频、女频
        if (data.audiences && Array.isArray(data.audiences)) {
            classes = data.audiences.map(audience => ({
                type_name: audience,
                type_id: audience
            }));
            
            // 为每个分类创建筛选条件
            data.audiences.forEach(audience => {
                filters[audience] = [];
                
                // 1. 标签筛选
                if (data.tags && Array.isArray(data.tags) && data.tags.length > 0) {
                    const tagValues = [{ n: '全部', v: '' }];
                    data.tags.forEach(tag => {
                        tagValues.push({ n: tag, v: tag });
                    });
                    filters[audience].push({
                        key: 'tag',
                        name: '标签',
                        value: tagValues
                    });
                }
                
                // 2. 排序筛选
                if (data.orders && Array.isArray(data.orders) && data.orders.length > 0) {
                    filters[audience].push({
                        key: 'order',
                        name: '排序',
                        value: data.orders.map(order => ({ n: order, v: order }))
                    });
                }
            });
        }
    }
    
    return JSON.stringify({ class: classes, filters: filters });
}

//推荐
async function homeVod(params) {
    const result = await category('全部', 1, {}, {});
    const data = typeof result === 'string' ? JSON.parse(result) : result;
    return JSON.stringify({ list: data.list || [] });
}

//分类页
async function category(tid, pg, filter, extend) {
    const videos = [];
    const page = pg || 1;
    
    // 从 extend 中获取筛选条件
    const tag = (extend && extend.tag) ? extend.tag : "";
    const order = (extend && extend.order) ? extend.order : "";
    
    // 根据排序参数映射到接口需要的值
    let orderValue = "";
    if (order === "最热") {
        orderValue = "hot";
    } else if (order === "最新") {
        orderValue = "new";
    }
    
    const postData = {
        "audience": tid === '全部' ? "" : tid,
        "page": page,
        "pageSize": 30,
        "searchWord": "",
        "subject": tag,
        "order": orderValue
    };
    
    const response = await request(`${rule.host}${rule.searchUrl}`, { 
        method: 'POST', 
        headers: {
            'User-Agent': UA,
            'Content-Type': 'application/json'
        },
        data: postData 
    });
    const res = JSON.parse(response);
    
    if (res && res.data) {
        res.data.forEach(it => {
            videos.push({
                vod_id: it.oneId,
                vod_name: it.title || '',
                vod_pic: it.vertPoster || '',
                vod_remarks: `集数:${it.episodeCount || 0} 播放:${it.viewCount || 0}`,
                vod_content: it.description || '',
                vod_year: it.publishDate || ''
            });
        });
    }
    
    return JSON.stringify({
        list: videos,
        page: page,
        pagecount: page + 1,
        limit: videos.length,
        total: videos.length * (page + 1)
    });
}

//详情页
async function detail(id) {
    const response = await request(`${rule.host}${rule.detailUrl}&oneId=${id}&page=1&pageSize=1000`, {
        headers: {
            'User-Agent': UA,
            'Content-Type': 'application/json'
        }
    });
    const res = JSON.parse(response);
    const data = res.data || [];
    const firstEpisode = data[0] || {};
    
    // 构建播放列表
    const playUrl = data.map(episode => {
        const episodeNum = episode.playOrder || episode.episodeNumber || 1;
        const playSetting = episode.playSetting || '';
        return `第${episodeNum}集$${playSetting}`;
    }).join('#');
    
    const vod = {
        vod_id: id,
        vod_name: firstEpisode.title || '',
        vod_pic: firstEpisode.vertPoster || '',
        vod_remarks: `共${data.length || 0}集`,
        vod_content: `播放量:${firstEpisode.collectionCount || 0}，评论:${firstEpisode.commentCount || 0} ${firstEpisode.description || ''}`,
        vod_play_from: '围观短剧',
        vod_play_url: playUrl
    };
    
    return JSON.stringify({ list: [vod] });
}

//播放页
async function play(flag, id, flags) {
    let playSetting;
    try {
        // 如果id已经是对象，直接使用；否则尝试解析
        if (typeof id === 'object') {
            playSetting = id;
        } else {
            playSetting = JSON.parse(id);
        }
    } catch (e) {
        return JSON.stringify({ parse: 0, url: id });
    }
    
    const videoUrl = playSetting.high || playSetting.normal || playSetting.super || '';
    
    return JSON.stringify({ 
        parse: 0, 
        url: videoUrl,
        header: {
            'User-Agent': UA
        }
    });
}

//搜索
async function search(wd, quick, pg) {
    let videos = [];
    const page = pg || 1;
    
    const postData = {
        "audience": "",
        "page": page,
        "pageSize": 30,
        "searchWord": wd,
        "subject": ""
    };
    
    const response = await request(`${rule.host}${rule.searchUrl}`, { 
        method: 'POST', 
        headers: {
            'User-Agent': UA,
            'Content-Type': 'application/json'
        }, 
        data: postData,
        timeout: 6000
    });
    
    const res = JSON.parse(response);
    if (res && res.data) {
        videos = res.data.map(it => ({
            vod_id: it.oneId || '',
            vod_name: it.title || '未知标题',
            vod_pic: it.vertPoster || '',
            vod_remarks: `集数:${it.episodeCount || 0}，播放:${it.viewCount || 0}`,
            vod_content: it.description || ''
        }));
    }
    
    return JSON.stringify({
        list: videos,
        page: page
    });
}

//请求函数
async function request(url, options = {}) {
    try {
        console.log(`【${siteName}】${options.method || 'GET'} ${url.split('?')[0]}`);
        
        let requestConfig = {
            method: options.method || 'GET',
            headers: { "User-Agent": UA, ...options.headers }
        };
        
        let contentType = requestConfig.headers['Content-Type'] || '';
        
        function stringifyData(data, format) {
            if (format.includes('json')) {
                return JSON.stringify(data);
            } else {
                const parts = [];
                for (let key in data) {
                    let value = data[key];
                    if (typeof value === 'object' && value !== null) {
                        value = JSON.stringify(value);
                    }
                    parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
                }
                return parts.join('&');
            }
        }
        
        let requestData = options.data || options.body;
        
        if (requestData) {
            if (typeof requestData === 'string') {
                requestConfig.body = requestData;
            } else if (typeof requestData === 'object') {
                if (!contentType) {
                    contentType = 'application/json';
                    requestConfig.headers['Content-Type'] = contentType;
                }
                requestConfig.body = stringifyData(requestData, contentType);
            }
        }
        
        const res = await req(url, requestConfig);
        return res.content || '';
    } catch (e) {
        console.log(`【${siteName}】请求失败: ${e.message}`);
        return '';
    }
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search
    };
}