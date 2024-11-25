// SPDX-FileCopyrightText: 2024 Tim Cocks
//
// SPDX-License-Identifier: MIT

/* bluesky scroller script.js */

// DOM Element references
let $template = document.querySelector("#postTemplate");
let $postWall = document.querySelector("#postWall");

// holds how many times we've fetched data. Used for filtering out older posts
let curFetchIndex = 0;

// list that will hold new post objects that have been fetched
let newPosts;

// flag to know whether the wall has been initialized
let initializedWall = false;

// gets callback when pywebview Api object is ready to be used
window.addEventListener('pywebviewready', function () {

    function fetchNewPosts() {
        /* Fetch posts, then initialize the wall if it hasn't been yet */

        pywebview.api.get_posts().then(function (posts) {
            console.log("fetching new data")
            if (!initializedWall) {
                buildPostWall(posts);

                // start the autoscroller
                setTimeout(function(){setInterval(autoScroll, 50);}, 2000);

                // set flag true so we know next time
                initializedWall = true

            } else { // wall was initialized already
                // just update the newPosts list
                newPosts = posts;
            }

            curFetchIndex += 1;
        });
    }

    // call fetch the first time
    fetchNewPosts();

    // set an interval to call fetch every 7 minutes
    setInterval(fetchNewPosts, 7 * 60 * 1000);
})

function inflatePostTemplate(postObj) {
    /* Takes an object represent the post to show and inflates
    * DOM elements and populates them with the post data. */

    let $post = $template.cloneNode(true);
    $post.removeAttribute("id");
    console.log($post);
    $post.setAttribute("data-fetch-index", curFetchIndex);
    $post.querySelector(".postAuthor").innerText = postObj["author"];
    $post.querySelector(".postText").innerText = postObj["text"];
    if(postObj.hasOwnProperty("image_file")){
        //$post.querySelector(".postImg").src = "../../.data/imgs/" + postObj["image_file"];
        $post.querySelector(".postImg").src = "imgs/" + postObj["image_file"];
    }else{
        $post.removeChild($post.querySelector(".postImg"));
    }

    $post.classList.remove("hidden");
    return $post;
}

function buildPostWall(posts) {
    /* Takes an object with a list of posts in it, inflates DOM elements
    * for each post in the data and adds it to the wall. */

    for (let i = 0; i < posts["posts"].length; i++) {
        let $post = inflatePostTemplate(posts["posts"][i])
        $postWall.appendChild($post);
    }
}

// gets callback any time a scroll event occurs
window.addEventListener('scroll', function () {
    // if scroll is past the boundary line
    if (window.scrollY > 1000) {
        // get the first post element from the top of the wall
        let $firstPost = $postWall.firstElementChild
        // remove it from the wall
        $postWall.removeChild($firstPost);

        // if there are no new posts currently
        if (newPosts === undefined || newPosts["posts"].length === 0) {
            // add the first post back to the wall at the bottom
            $postWall.appendChild($firstPost);

        } else { // there are new posts to start showing

            // inflate the first new post
            $newPost = inflatePostTemplate(newPosts["posts"].shift());
            // add it to the post wall
            $postWall.appendChild($newPost);

            // if the post we removed from the top is still current
            if ($firstPost.getAttribute("data-fetch-index") === curFetchIndex) {
                // add it back in at the bottom
                $postWall.appendChild($firstPost);
            }
        }
    }
});

function autoScroll() {
    /* Function to be called frequently to automatically scroll the page.
    * Also calls check_quit() to allow python to handle KeyboardInterrupt */
    pywebview.api.check_quit();
    window.scrollBy(0, 2);
}
