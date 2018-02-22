# -*- coding: UTF-8 -*-

import requests
import pymongo
import json
import re
import sys
from bs4 import BeautifulSoup
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from requests.adapters import HTTPAdapter
import logging

class Byr:

	def __init__(self):

		# global requests
		self.host = "http://m.byr.cn"
		self.session = requests.Session()
		self.session.headers = {'Connection': 'close'}
		self.session.keep_alive = False
		self.session.mount(self.host, HTTPAdapter(max_retries=30))

		# login params
		self.id = 'username'
		self.passwd = 'password'

		# connect mongo
		mongoUrl = 'mongodb://username:password@ip/database?authMechanism=MONGODB-CR'
		self.mongo = pymongo.MongoClient(mongoUrl)
		self.db = self.mongo.byr

		# default update page num in board
		self.updatepageForBoard = 2

		# default update page num in article
		self.updatepageForArticle = 15

		# the timeout value of request
		self.timeout = 10

		# command params, init/update, links/articles
		if len(sys.argv) > 1 and sys.argv[1] == 'init':
			self.isInit = True
			print 'Run As Init.'
		elif len(sys.argv) > 1 and sys.argv[1] == 'update':
			self.isInit = False
			print 'Run As Update.'
		else:
			print 'Lack Of Parameter. Exit.'
			exit()

		# the boards not crawl
		self.excludeBoards = [  'http://m.byr.cn/board/Ticket', 
							    'http://m.byr.cn/board/JobInfo', 
								'http://m.byr.cn/board/Jump', 
								'http://m.byr.cn/board/Weather',
								'http://m.byr.cn/board/ParttimeJob', 
								'http://m.byr.cn/board/LostandFound', 
								'http://m.byr.cn/board/BBSLists', 
								'http://m.byr.cn/board/cnLists', 
								'http://m.byr.cn/board/cnTest', 
								'http://m.byr.cn/board/Score',
								'http://m.byr.cn/board/BUPTPost',
								'http://m.byr.cn/board/BBSMan_Dev',
								'http://m.byr.cn/board/Advertising',
								'http://m.byr.cn/board/BookTrade',
								'http://m.byr.cn/board/Co_Buying',
								'http://m.byr.cn/board/ComputerTrade',
								'http://m.byr.cn/board/test' ]

		# log params
		self.LoggingFormat = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s'
		self.DateFormat = '%Y-%m-%d %H:%M:%S'

	# login
	def login(self, crawlLogger):

		crawlLogger.info('Crawl %s Begin.' % self.host)

		# login
		crawlLogger.info('Login Begin.')
		logindata = {'id': self.id, 'passwd': self.passwd}
		loginurl = 'http://m.byr.cn/user/login'
		loginresponse = self.session.post(loginurl, data=logindata, allow_redirects=False)
		if loginresponse.status_code == 302:
			crawlLogger.info('Login Successed.')
		else:
			crawlLogger.info('Login Failed.')
			return
		crawlLogger.info('Login End.')

	# get all sections
	def getAllSections(self, crawlLogger):

		crawlLogger.info('Crawl Sections Begin.')
		sectionRoot = '/section'
		self.getSections(sectionRoot, crawlLogger)
		crawlLogger.info('Crawl Sections End.')

	# get all sections from root, use recursion
	def getSections(self, parent, crawlLogger):

		# get all 'li' from the parent url response
		parentByrUrl = self.host + parent
		sectionResponse = self.postRequestUntilSucc(parentByrUrl)
		sectionSoup = BeautifulSoup(sectionResponse.text, 'lxml')
		sectionLis = sectionSoup.body.select('li')

		# traverse all 'li'
		for sectionLi in sectionLis:
			sectionId = sectionLi.a.get('href')
			sectionByrUrl = self.host + sectionId
			sectionTitle = sectionLi.a.string
			if sectionLi.font is not None:
				sectionType = '1'
			else:
				sectionType = '0'

			# if not exist, insert into db.
			if self.db.sections.find_one({'_id': sectionId}) is None:
				self.db.sections.insert({'_id'			: sectionId, 
										 'title'		: sectionTitle, 
										 'byrurl'		: sectionByrUrl, 
										 'type'			: sectionType, 
										 'parent'		: parent})
				crawlLogger.info('Section %s Insert Successed.' % sectionByrUrl)
			else:
				crawlLogger.info('Section %s Existed.' % sectionByrUrl)

			# if sectiontype == '1', get children section
			if sectionType == '1':
				self.getSections(sectionId, crawlLogger)

	# remove all links and articles if init
	def removeAllIfInit(self):

		if self.isInit:
			print 'Remove All Links And All Articles Begin.'
			self.db.links.delete_many({})
			self.db.articles.delete_many({})
			print 'Remove All Links And All Articles End.'

	# post the request until success
	def postRequestUntilSucc(self, url):

		success = False
		while success is not True:
			try:
				response = self.session.post(url, timeout=self.timeout)
			except Exception as e:
				print e
				time.sleep(self.timeout)
			else:
				success = True
		return response

	# get All Links
	def getAllLinks(self, crawlLogger):

		crawlLogger.info('Get Links Begin.')
		# traverse all section which type == 0, this cursor no timeout
		sections = self.db.sections.find({'type': '0'}, no_cursor_timeout=True)
		for section in sections:

			# get board url from section
			boardByrUrl = section.get('byrurl')
			board = section.get('_id')

			# if board is excluded, continue
			if boardByrUrl in self.excludeBoards:
				continue

			# request board, get form
			boardResponse = self.postRequestUntilSucc(boardByrUrl)
			boardSoup = BeautifulSoup(boardResponse.text, 'lxml')
			form = boardSoup.body.form
			pageCount = self.getPageCountFromForm(form, boardByrUrl, crawlLogger)

			# if init, use pagecount, else, use the min, to update
			if self.isInit == False:
				pageCount = min(pageCount, self.updatepageForBoard)

			# traverse all pages, get the links in page
			for page in range(1, pageCount):

				# request page
				pageUrl = boardByrUrl + '?p=' + unicode(page)
				pageResponse = self.postRequestUntilSucc(pageUrl)
				pageSoup = BeautifulSoup(pageResponse.text, 'lxml')

				pageLis = pageSoup.body.select('li')
				for pageLi in pageLis:

					# get link
					linkStrings = list(pageLi.stripped_strings)
					if len(linkStrings) >= 4:
						linkTitle = linkStrings[0]
						linkReply = re.search(r'\d+', linkStrings[1]).group()
						linkDate = linkStrings[2]
						linkAuthor = linkStrings[3]
						linkId = pageLi.a.get('href')
						linkByrUrl = self.host + linkId

						# if link not exist, insert into db, else update it
						if self.db.links.find_one({'_id': linkId}) is None:
							self.db.links.insert({'_id': linkId, 
												  'title': linkTitle, 
												  'byrurl': linkByrUrl, 
												  'reply': linkReply, 
												  'author': linkAuthor, 
												  'date': linkDate, 
												  'board': board,
												  'status': '1'})
							crawlLogger.info('Link %s Insert Successed.' % linkByrUrl)
						else:
							self.db.links.update({'_id': linkId}, 
												 {'$set': {'title': linkTitle, 
												 		   'byrurl': linkByrUrl, 
												 		   'reply': linkReply, 
												 		   'author': linkAuthor, 
												 		   'date': linkDate, 
												 		   'board': board,
												  		   'status': '1'}})
							crawlLogger.info('Link %s Update Successed.' % linkByrUrl)
						#sleep(0.2)

		# close the cursor explicitly
		sections.close()
		crawlLogger.info('Get Links End.')

	# get pagecount from form
	def getPageCountFromForm(self, form, url, crawlLogger):

		if form is not None:
			# the link has deleted, remove the link
			if form.get('action') == '/go':
				self.db.links.remove({'_id': url})
				crawlLogger.info('Link %s Get Form Failed.' % url)
				return 0
			else:
				pagegroup = re.search(r'(?<=/).*', unicode(form.find('a', 'plant').string))
				if pagegroup is not None:
					pagecount = int(pagegroup.group())
				else:
					crawlLogger.info('Link %s Get Page Count Failed.' % url)
					exit()
		else:
			crawlLogger.info('Link %s Get Form Failed.' % url)
			return 0
		return pagecount + 1

	# get Articles
	def getArticles(self, crawlLogger):

		crawlLogger.info('Get Articles Begin.')
		links = self.db.links.find({'status': '1'}, no_cursor_timeout=True)
		for link in links:

			linkId = link.get('_id')
			linkByrUrl = link.get('byrurl')

			# request link, get form
			linkResponse = self.postRequestUntilSucc(linkByrUrl)
			if linkResponse.status_code == 200:
				linkSoup = BeautifulSoup(linkResponse.text, 'lxml')
				form = linkSoup.body.form
				pageCount = self.getPageCountFromForm(form, linkByrUrl, crawlLogger)
			else:
				self.db.links.remove({'_id': linkId})
				self.db.articles.remove({'link': linkId})
				continue

			# page cannot open, continue
			if pageCount == 0:
				self.db.links.remove({'_id': linkId})
				self.db.articles.remove({'link': linkId})
				continue

			# get the article count in this link
			articleCount = self.db.articles.find({'link': linkId})

			if self.isInit or pageCount <= self.updatepageForArticle or articleCount == 0:
				# remove all articles in this link
				self.db.articles.remove({'link': linkId})
				crawlLogger.info('Remove Articels in %s Completed.' % linkId)
				fromPage = 1
			else:
				# old link only update updatepageForArticle pages
				crawlLogger.info('Pagecount of this old link is so large, only crawl update.')
				fromPage = pageCount - self.updatepageForArticle

			# traverse all pages, get the articles in page
			allpage = True
			for page in range(fromPage, pageCount):
				
				# request page
				pageByrUrl = linkByrUrl + '?p=' + unicode(page)
				pageResponse = self.postRequestUntilSucc(pageByrUrl)

				if pageResponse.status_code == 200:
					pageSoup = BeautifulSoup(pageResponse.text, 'lxml')
					pageLis = pageSoup.body.select('li')
					for pageLi in pageLis:
						if pageLi.a and pageLi.a.get('name'):
							floorId = re.search(r'\d+', pageLi.a.get('name')).group()
							div1 = list(pageLi.find('div', 'nav hl').stripped_strings)
							author = div1[2]
							pubtime = div1[4]
							div2 = list(pageLi.find('div', 'sp').stripped_strings)
							div2.pop()
							content = ""
							for e in div2:
								content += e
								content += '<br/>'
							articleId = linkId + '?a=' + floorId

							# if link not exist, insert into db, else update it
							if self.db.articles.find_one({'_id': articleId}) is None:
								self.db.articles.insert({'_id': articleId, 
												  	 	 'floorid': floorId, 
												  	 	 'author': author, 
												  	 	 'pubtime': pubtime, 
													 	 'content': content,
													 	 'link': linkId})
								crawlLogger.info('Article %s Insert Successed.' % articleId)
							else:
								self.db.articles.update({'_id': articleId}, 
													 	{'$set': {'_id': articleId, 
												  	 	 		  'floorid': floorId, 
												  	 	 		  'author': author, 
												  	 	 		  'pubtime': pubtime, 
													 	 		  'content': content,
													 	 		  'link': linkId}})
								crawlLogger.info('Article %s Update Successed.' % articleId)

							
							#sleep(0.2)
				else:
					# if request failed, break
					allpage = False
					break
			# if all pages in this link crawled success, set the link status 0
			if allpage:
				self.db.links.update({'_id': linkId}, {'$set': {'status': '0'}})

		# close the cursor explicitly
		links.close()
		crawlLogger.info('Get Articles End.')

	# logout
	def logout(self, crawlLogger):

		crawlLogger.info('Logout Begin.')
		logouturl = 'http://m.byr.cn/user/logout'
		logoutresponse = self.session.post(logouturl, allow_redirects=False)
		if logoutresponse.status_code == 302:
			crawlLogger.info('Logout Successed.')
		else:
			crawlLogger.info('Logout Failed.')
			return
		crawlLogger.info('Logout End.')

		self.mongo.close()
		crawlLogger.info('Crawl %s End.' % self.host)

	def startSchedulerTask(self):

		crawlHandler = logging.FileHandler('logs/'+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))+'.log')
		crawlHandler.level = logging.INFO
		crawlHandler.formatter = logging.Formatter(self.LoggingFormat, self.DateFormat)
		crawlLogger = logging.getLogger("crawl")
		crawlLogger.addHandler(crawlHandler)

		# login
		self.login(crawlLogger)

		beginTime = time.time()
		crawlLogger.info('Now is %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(beginTime)))

		# get all section
		self.getAllSections(crawlLogger)
		sectionEndtime = time.time()
		crawlLogger.info('Now is %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sectionEndtime)))

		# get All Links
		self.getAllLinks(crawlLogger)
		linkEndtime = time.time()
		crawlLogger.info('Now is %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(linkEndtime)))

		# get articles from links where status = 1
		# get articles only once every day
		nowHour = time.localtime(time.time()).tm_hour
		if nowHour > 0 and nowHour < 4:
			self.getArticles(crawlLogger)
		articleEndtime = time.time()
		crawlLogger.info('Now is %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(articleEndtime)))

		# logout
		self.logout(crawlLogger)

		crawlLogger.info('Sections Crawl Cost Time: %.0f seconds.' % (sectionEndtime - beginTime))
		crawlLogger.info('Links Crawl Cost Time: %.0f seconds.' % (linkEndtime - sectionEndtime))
		crawlLogger.info('Articles Crawl Cost Time: %.0f seconds.' % (articleEndtime - linkEndtime))
		crawlLogger.info('Total Crawl Cost Time: %.0f seconds.' % (articleEndtime - beginTime))

		crawlLogger.removeHandler(crawlHandler)

	def main(self):

		logging.basicConfig(level=logging.INFO)

		# remove all links and articles if init
		self.removeAllIfInit()

		# start scheduler for sections and links
		scheduler = BlockingScheduler()
		scheduler.add_job(self.startSchedulerTask, 'cron', hour='0,6,9,12,15,18,21', minute='0')
		try:
			scheduler.start()
		except Exception as e:
			scheduler.shutdown()

		self.startSchedulerTask()

byr = Byr()
byr.main()