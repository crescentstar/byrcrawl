var express = require('express');
var router = express.Router();

router.get('/', function(req, res) {
    var db = req.db;
    var collection = db.get('sections');
    collection.find({'parent': '/section'}, {sort: {'_id': 1}}, function(e, sections) {
        // res.render('section', {
        //     'sections' : sections,
        //     'root'     : '0'
        // });
        res.json(sections);
    });
});

router.get('/:sectionid', function(req, res) {
    var db = req.db;
    var collection = db.get('sections');
    var parentId = '/section/' + req.params.sectionid;
    var returnLink = '';

    // 查出上一层的parent
    collection.findOne({'_id': parentId}, {castIds: false}, function(e, parentSection) {
        returnLink = parentSection.parent;
        collection.find({'parent': parentId}, {sort: {'_id': 1}}, function(e, sections) {
	        // res.render('section', {
	        //     'sections'   : sections,
	        //     'root'     	 : '1',
	        //     'returnLink' : returnLink,
	        // });
            res.json(sections);
	    });
    });
});

module.exports = router;
