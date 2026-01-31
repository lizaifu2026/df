const siteUrl = 'https://djapi.x5xkj.com';
const headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; 23116PN5BC Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36 uni-app Html5Plus/1.0 (Immersed/0.6666667)'
};

async function home(filter) {
    const classes = [
        {'type_id': 'type', 'type_name': '短剧'},
        {'type_id': 'type1', 'type_name': '电影'},
        {'type_id': 'type2', 'type_name': '连续剧'},
        {'type_id': 'type3', 'type_name': '动漫'},
        {'type_id': 'type4', 'type_name': '综艺'},
        {'type_id': 'type5', 'type_name': '体育'}
    ];
    const filterObj = {};
    const promises = classes.map(async (cls) => {
        const typeId = cls.type_id;
        const url = `${siteUrl}/api/video/category?type=${typeId}&page=1&limit=100`;
        try {
            const json = await request(url);
            if (json.data && json.data.list && json.data.list.length > 0) {
                const valueList = json.data.list.map(item => ({
                    n: item.name,
                    v: item.id.toString()
                }));
                const firstValue = valueList.length > 0 ? valueList[0].v : '';
                filterObj[typeId] = [{
                    key: 'cateId',
                    name: '分类',
                    init: firstValue,
                    value: valueList
                }];
            }
        } catch (e) {}
    });
    await Promise.all(promises);
    return JSON.stringify({
        class: classes,
        filters: filterObj
    });
}

async function homeVod() {
    return JSON.stringify({ list: [] });
}

async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    let categoryId = extend.cateId;
    if (!categoryId) {
        try {
            const cateUrl = `${siteUrl}/api/video/category?type=${tid}&page=1&limit=100`;
            const cateJson = await request(cateUrl);
            if (cateJson.data && cateJson.data.list && cateJson.data.list.length > 0) {
                categoryId = cateJson.data.list[0].id;
            }
        } catch (e) {}
    }
    if (!categoryId) {
        return JSON.stringify({ list: [], page: pg, limit: 20, total: 0 });
    }
    const link = `${siteUrl}/api/video/list?category_id=${categoryId}&page=${pg}&limit=20`;
    const json = await request(link);
    const videos = [];
    if (json.data && json.data.list) {
        json.data.list.forEach(item => {
            videos.push({
                vod_id: item.id.toString(),
                vod_name: item.name,
                vod_pic: item.img,
                vod_remarks: item.sub_title || item.rating
            });
        });
    }
    return JSON.stringify({
        list: videos,
        page: parseInt(json.data.page),
        pagecount: json.data.has_more ? parseInt(json.data.page) + 1 : parseInt(json.data.page),
        limit: 20,
        total: json.data.total
    });
}

async function search(wd, quick, pg=1) {
    if (!pg || pg <= 0) pg = 1;
    const limit = 10;
    const offset = (pg - 1) * limit;
    const url = `${siteUrl}/api/video/lists?limit=${limit}&offset=${offset}&keytext=${encodeURIComponent(wd)}`;
    console.log(url)
    const json = await request(url);
    const videos = [];
    if (json.rows && json.rows.length > 0) {
        json.rows.forEach(item => {
            let vId = item.id;
            if (!vId || vId === 0) {
                vId = item.vod_id;
            }
            videos.push({
                vod_id: vId.toString(),
                vod_name: item.name,
                vod_pic: item.img,
                vod_remarks: item.tp || item.type || '',
                vod_year: item.createtime ? new Date(item.createtime * 1000).getFullYear().toString() : ''
            });
        });
    }
    const total = json.total || 0;
    const pagecount = total === 0 ? 0 : Math.ceil(total / limit);
    return JSON.stringify({list: videos, page: parseInt(pg), pagecount: pagecount, limit: limit, total: total});
}

async function detail(id) {
    const url = `${siteUrl}/api/video/videoinfo?page=1&uid=0&vid=${id}&mid=0&token=undefined`;
    try {
        const json = await request(url);
        const info = json.videodata || {};
        const eps = json.data || [];
        const playUrlList = eps.map(ep => `${ep.name}$${ep.videourl}`).join('#');
        const vod = {
            vod_id: id,
            vod_name: info.name || '',
            vod_pic: info.img || '',
            vod_type: info.type || '',
            vod_year: info.yearq || '',
            vod_area: info.adddd || '',
            vod_remarks: info.tp || (info.zcount ? info.zcount + '集' : ''),
            vod_actor: info.yyid || '',
            vod_director: info.director || '',
            vod_content: formatContent(info.info || ''),
            vod_play_from: info.cj_nema || '默认线路',
            vod_play_url: playUrlList
        };
        return JSON.stringify({ list: [vod] });
    } catch (e) {
        return JSON.stringify({ list: [] });
    }
}

async function play(flag, id, flags) {
    return JSON.stringify({
        parse: 0,
        url: id,
        header: headers
    });
}

async function request(reqUrl) {
    const res = await req(reqUrl, {
        method: 'GET',
        headers: headers
    });
    return JSON.parse(res.content);
}

function formatContent(content) {
    if (!content) return '';
    return content.replace(/<[^>]+>/g, "").replace(/\s+/g, " ");
}

async function init(cfg) {}

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