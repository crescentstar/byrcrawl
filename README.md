# byrcrawl
Crawl byr bbs by python, and display it by express.

从零开始爬取byr论坛并展现

1. 服务器
我选择的是aliyun，安装了Ubuntu 16.04.1 LTS。云主机的出现以及其便利性，使得我们开发一个公开的网站服务及其便捷。

2. 域名
aliyun与万网合作，可以在aliyun的控制台方便的申请域名，由于一些比较好的域名在那次轰轰烈烈的byr论坛即将关闭的风波中被各校友抢注，我只能注册了http://www.byrforum.cn/。在控制台中，配置一条记录类型为A的域名解析，解析http://www.byrforum.cn/至aliyun服务器ip即可。
当然了，如果想正常访问网站，需要有备案流程。

3. HTTP服务器
HTTP服务器采用了主流的nginx，我安装的版本是nginx/1.10.0 (Ubuntu)。nginx的安装与配置网上教程就太多了，不再赘述。在nginx.conf中配置www.byrforum.cn的监控，设置好root即可。
其实node.js自身就是个HTTP服务器，但由于我有多个域名指向我的aliyun服务器，所以还是需要用nginx做反向代理，将请求转给node.js。

4. 数据库
由于爬取的数据基本都是文档，而且我们是非交易系统，所以我选择了MongoDB而不是MySQL。我安装的MongoDB版本是2.6.10，最新版是3.x。
MongoDB的安装很简单，网上教程也非常多，在此不多赘述。但MongoDB的用户配置还是与传统的关系型数据库区别很大，这一点在安装配置时需要多关注。

5. 爬虫
爬虫采用主流的python，由于我的Mac以及aliyun主机上自带的python版本都是2.7，所以我采用了此版本，并没有用最新的3.x。
在使用python爬取byr论坛的过程中，遇到了几个问题，详情可见：http://www.wuzhou-crescent.com/?p=71

6. WEB页面
直接采用了express搭建，使用组件monk非常方便的展现MongoDB里的数据。使用express需要在服务器上安装node，我使用的是v6.11.2。

7. 部署
7.1 下载本工程，将代码拷贝至nginx的web目录，默认是/var/www。
7.2 修改express文件夹下的app.js，输入MongoDB的用户名、密码、ip、数据库名称，先运行npm install进行项目初始化，然后运行sudo nohup npm run start启动express。 
7.3 修改crawl文件夹下的index.py，输入您byr论坛的用户名、密码，MongoDB的用户名、密码、ip、数据库名称，然后运行sudo nohup python index.py init进行初始化，或者sudo nohup python index.py update进行更新。

8. 成果展现
访问http://www.byrforum.cn/，可见爬取的具体内容。（暂时没有美化页面）该爬虫从2017年年中运行至今，从未报错中断，非常稳定。