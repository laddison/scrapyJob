import scrapy
import json
from job.items import JobItem

class HockeyAppSpider(scrapy.Spider):
    # 定制化设置
    custom_settings = {
        'LOG_LEVEL': 'DEBUG',  # Log等级，默认是最低级别debug
        'ROBOTSTXT_OBEY': False,  # default Obey robots.txt rules
        'DOWNLOAD_DELAY': 2,  # 下载延时，默认是0
        'COOKIES_ENABLED': True,  # 默认enable，爬取登录后的数据时需要启用。 会增加流量，因为request和response中会多携带cookie的部分
        'COOKIES_DEBUG': True, # 默认值为False,如果启用，Scrapy将记录所有在request(Cookie 请求头)发送的cookies及response接收到的cookies(Set-Cookie 接收头)。
        'DOWNLOAD_TIMEOUT': 25,  # 下载超时，既可以是爬虫全局统一控制，也可以在具体请求中填入到Request.meta中，Request.meta['download_timeout']
    }

    name = "hock"
    host = "https://rink.hockeyapp.net/"
    username = "*************" # 账号
    password = "*************" # 密码
    headerData = {
        "Referer": "https://rink.hockeyapp.net/users/sign_in",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    }

    # 第一步：爬取登录页面
    def start_requests(self):
        print("start clawer")
        loginUrl = "https://rink.hockeyapp.net/users/sign_in"
        loginIndexReq = scrapy.Request(
            url=loginUrl,
            headers=self.headerData,
            callback=self.parseLoginPage,
            dont_filter=True,  # 防止页面因为重复爬取，被过滤了
        )
        yield loginIndexReq

    # 第二步：分析登录页面，取出必要的参数，然后发起登录请求POST
    def parseLoginPage(self, response):
        authenticity_token = response.xpath('//form[@class="form-horizontal"]/div/input[@name="authenticity_token"]/@value').extract_first()
        print(f"parseLoginPage: url = {response.url}")

        yield scrapy.FormRequest(
            url="https://rink.hockeyapp.net/users/sign_in",
            method='POST',
            dont_filter=True,
            headers=self.headerData,
            formdata={
                'what': 'sign_in',
                'utf8': '✓',
                'authenticity_token':str(authenticity_token),
                'invite_token': '',
                'to': '',
                'demo': '',
                'secret': '',
                'commit': 'Sign In',
                'user[email]': 'wl3175924472@gmail.com',
                'user[password]': 'wanglewangluo520!@#',
                'user[remember_me]': '1'
            },
            callback=self.loginResParse
        )

    # 第三步：分析登录结果，然后发起登录状态的验证请求
    def loginResParse(self, response):
        print(f"loginResParse: url = {response.url}")

        # 通过访问个人中心页面的返回状态码来判断是否为登录状态
        # 这个页面，只有登录过的用户，才能访问。否则会被重定向(302) 到登录页面
        routeUrl = "https://rink.hockeyapp.net/manage/dashboard"
        # 下面有两个关键点
        # 第一个是header，如果不设置，会返回500的错误
        # 第二个是dont_redirect，设置为True时，是不允许重定向，用户处于非登录状态时，是无法进入这个页面的，服务器返回302错误。
        #       dont_redirect，如果设置为False，允许重定向，进入这个页面时，会自动跳转到登录页面。会把登录页面抓下来。返回200的状态码
        yield scrapy.Request(
            url=routeUrl,
            headers=self.headerData,
            meta={
                'dont_redirect': True,  # 禁止网页重定向302, 如果设置这个，但是页面又一定要跳转，那么爬虫会异常
                # 'handle_httpstatus_list': [301, 302]      # 对哪些异常返回进行处理
            },
            callback=self.isLoginStatusParse,
            dont_filter=True,
        )

    # 第五步:分析用户的登录状态, 如果登录成功，那么接着爬取其他页面
    # 如果登录失败，爬虫会直接终止。
    def isLoginStatusParse(self, response):
        print(f"isLoginStatusParse: url = {response.url}")

        # 如果能进到这一步，都没有出错的话，那么后面就可以用登录状态，访问后面的页面了
        # ………………………………
        # 不需要存储cookie
        # 其他网页爬取
        # ………………………………
        yield scrapy.Request(
            url="https://rink.hockeyapp.net/manage/dashboard",
            headers=self.headerData,
            # 如果不指定callback，那么默认会使用parse函数
        )

    def parse(self, response):
        authenticity_token = response.xpath('//div/input[@name="authenticity_token"]/@value').extract_first()

        for sel in response.xpath('//div[@class="apps columns hidden truncate"]/ul/li'):
            item = JobItem()
            appName = sel.xpath('@data-search').extract_first()
            appUrl = sel.xpath('a/@href').extract_first();
            newUserUrl = 'https://rink.hockeyapp.net'+ appUrl + '/statistics_insights?what=new_users&filter_app_version_id=-1&filter_app_version=null&filter_custom_event_name=null&filter_hours=null'
            activeUserUrl = 'https://rink.hockeyapp.net'+ appUrl + '/statistics_insights?what=users&filter_app_version_id=-1&filter_app_version=null&filter_custom_event_name=null&filter_hours=null'
            print(appName)
            item['appName'] = appName

            yield scrapy.Request(
                url=newUserUrl,
                headers={
                    'Referer': 'https://rink.hockeyapp.net' + appUrl,
                    'X-CSRF-Token': str(authenticity_token),
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ar;q=0.6',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Host': 'rink.hockeyapp.net',
                    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
                },
                callback=self.getNewUserData,
                dont_filter=True,
                meta={'activeUserUrl': activeUserUrl, 'appUrl': appUrl, 'authenticity_token': authenticity_token, 'item': item},
            )

    def getNewUserData(self, response):
        data = json.loads(response.body);

        activeUserUrl = response.meta.get('activeUserUrl')
        appUrl = response.meta.get('appUrl')
        authenticity_token = response.meta.get('authenticity_token')
        item = response.meta.get('item')
        item['newData'] = data

        yield scrapy.Request(
            url=activeUserUrl,
            headers={
                'Referer': 'https://rink.hockeyapp.net' + appUrl,
                'X-CSRF-Token': str(authenticity_token),
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ar;q=0.6',
                'X-Requested-With': 'XMLHttpRequest',
                'Host': 'rink.hockeyapp.net',
                'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
            },
            callback=self.getActiveUserData,
            dont_filter=True,
            meta={'activeUserUrl': activeUserUrl, 'item':item},
        )

    def getActiveUserData(self, response):
        data = json.loads(response.body);
        item = response.meta.get('item')
        item['activeData'] = data
        yield item
