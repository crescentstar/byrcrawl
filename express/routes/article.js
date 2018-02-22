var express = require('express');
var router = express.Router();

var pageCount = 10;

router.get('/:boardId/:articleId', function(req, res) {
    
    var pageId = req.query.p ? req.query.p : 1;
    var db = req.db;
    var collection = db.get('articles');
    var board = req.params.boardId;
    var link = '/article/' + board + '/' + req.params.articleId;
    var skipNum = pageCount * (pageId - 1);
    var prev = parseInt(pageId) - 1;
    var next = parseInt(pageId) + 1;
    var totalPage = '';

    // total page
    collection.count({'link': link}, function(e, count){
        totalPage = Math.floor((count - 1) / pageCount + 1);
        collection.find({'link': link}, {sort: {'pubtime': 1}, skip: skipNum, limit: pageCount}, function(e, articles) {
            // res.render('article', {
            //     'articles'  : articles,
            //     'pageId'    : pageId,
            //     'prev'      : prev,
            //     'next'      : next,
            //     'totalPage' : totalPage,
            //     'board'     : board
            // });
            res.json(articles);
        });
    }); 
});

module.exports = router;
