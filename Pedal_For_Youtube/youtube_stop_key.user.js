// ==UserScript==
// @name          Youtube Pause Key
// @version       1
// @namespace     http://unpythonic.net.com/youtube-pause-key
// @include       http://youtube.com/*
// @include       https://youtube.com/*
// @include       http://www.youtube.com/*
// @include       https://www.youtube.com/*
// @grant none
// ==/UserScript==

(function () {
    var inject = function() {
        var is_press_key = function (e, key) {
            document.last_target = e.target;
            document.last_event = e;
            var keyCode = e.keyCode ? e.keyCode : e.which;
            return (! (e.altKey || e.ctrlKey || e.metaKey)
                    && keyCode == key);
        }

        var gr_in_bg_event = function(e) {
            var pause_key = 112; // 'p' key
            var videos = e.target.getElementsByTagName('video');
            if(videos.length == 0) { return true; }
            if (is_press_key(e, pause_key)) {
                videos[0].pause();
                e.stopPropagation();
                e.preventDefault();
                return;
            }
            return true;
        }

        document.addEventListener("keypress", gr_in_bg_event, true);
    }

    var newel = document.createElement("script");
    var newcontent = document.createTextNode("(" + inject + ")()")
    newel.appendChild(newcontent);
    document.body.appendChild(newel);
})()
