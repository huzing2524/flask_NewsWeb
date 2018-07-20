let currentCid = 1; // 当前分类 id
let cur_page = 1; // 当前页
let total_page = 1;  // 总页数
let data_querying = true;   // 是否正在向后台获取数据

$(function () {
    // 界面加载完成之后去加载新闻数据
    updateNewsData();

    // 首页分类切换
    $('.menu li').click(function () {
        // 取到指定分类的cid
        let clickCid = $(this).attr('data-cid');
        // 遍历所有的 li 移除身上的选中效果
        $('.menu li').each(function () {
            $(this).removeClass('active')
        });
        // 给当前分类添加选中的状态
        $(this).addClass('active');
        // 如果点击的分类与当前分类不一致
        if (clickCid != currentCid) {
            // 记录当前分类id
            currentCid = clickCid;

            // 重置分页参数
            cur_page = 1;
            total_page = 1;
            updateNewsData()
        }
    });

    //页面滚动加载相关
    $(window).scroll(function () {

        // 浏览器窗口高度
        let showHeight = $(window).height();

        // 整个网页的高度
        let pageHeight = $(document).height();

        // 页面可以滚动的距离
        let canScrollHeight = pageHeight - showHeight;

        // 页面滚动了多少,这个是随着页面滚动实时变化的
        let nowScroll = $(document).scrollTop();

        if ((canScrollHeight - nowScroll) < 100) {
            // 判断页数，去更新新闻数据；data_querying 控制数据查询的状态，每次往页底拖动只加载下一页，防止一次加载多页数据但是不会全部显示出来，浪费有问题
            if (!data_querying) {
                data_querying = true;
                // 当前页小于总页数
                if (cur_page < total_page) {
                    cur_page += 1;
                    updateNewsData();
                }
            }
        }
    });
});

function updateNewsData() {
    // 更新新闻数据
    let params = {
        "cid": currentCid,
        "page": cur_page
    };
    $.get("/news_list", params, function (resp) {
        // 数据加载完毕，设置【正在加载数据】的变量为 false 代表当前没有在加载数据
        data_querying = false;
        if (resp.errno == "0") {
            // 给总页数据赋值
            total_page = resp.data.total_page;
            // 代表请求成功,清除已有数据
            // 进入网站默认显示第一页，不管是查看 最新 分类或者其它分类时，都需要清空原有内置的html模板数据
            if (cur_page == 1) {
                $(".list_con").html("");
            }
            // 添加请求成功之后返回的数据
            // 显示数据
            for (let i = 0; i < resp.data.news_dict_li.length; i++) {
                let news = resp.data.news_dict_li[i];
                let content = '<li>';
                content += '<a href="/news/' + news.id + '" class="news_pic fl"><img src="' + news.index_image_url + '?imageView2/1/w/170/h/170"></a>';
                content += '<a href="/news/' + news.id + '" class="news_title fl">' + news.title + '</a>';
                content += '<a href="/news/' + news.id + '" class="news_detail fl">' + news.digest + '</a>';
                content += '<div class="author_info fl">';
                content += '<div class="source fl">来源：' + news.source + '</div>';
                content += '<div class="time fl">' + news.create_time + '</div>';
                content += '</div>';
                content += '</li>';
                $(".list_con").append(content)
            }
        }
        else {
            // 请求失败
            alert(resp.errmsg);
        }
    })
}
