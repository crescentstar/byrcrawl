var express = require('express');
var router = express.Router();

var pageCount = 10;

router.get('/:boardId', function(req, res) {
    
    var pageId = req.query.p ? req.query.p : 1;
    var db = req.db;
    var collection = db.get('links');
    var board = '/board/' + req.params.boardId;
    var skipNum = pageCount * (pageId - 1);
    var prev = parseInt(pageId) - 1;
    var next = parseInt(pageId) + 1;
    var totalPage = '';

    // total page
    collection.count({'board': board}, function(e, count){
        totalPage = Math.floor((count - 1) / pageCount + 1);
        collection.find({'board': board}, {sort: {'date': -1}, skip: skipNum, limit: pageCount}, function(e, links) {
            // res.render('board', {
            //     'links'     : links,
            //     'pageId'    : pageId,
            //     'prev'      : prev,
            //     'next'      : next,
            //     'totalPage' : totalPage
            // });
            res.json(links);
        });
    }); 
});

module.exports = router;
