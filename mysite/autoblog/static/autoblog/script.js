document.getElementById("blog-form").addEventListener("submit", () => {
    var title = document.getElementById("title").innerText;
    document.getElementById("id_title").value = title;

    getAndSaveContent("subheading_1", "section_1");
    getAndSaveContent("subheading_2", "section_2");
    getAndSaveContent("subheading_3", "section_3");
    getAndSaveContent("subheading_4", "section_4");
    getAndSaveContent("subheading_5", "section_5");
});

function getAndSaveContent(subheading, section) {
    var subheading_text = document.getElementById(subheading).innerText;
    document.getElementById("id_" + subheading).value = subheading_text;

    var section_text = document.getElementById(section).innerText
    document.getElementById("id_" + section).value = section_text;
}

function navResizeMobile() {
    var navContainer = document.getElementById("nav-container");
    
    if (navContainer.style.width === "0px" || navContainer.style.width === '') {
        navContainer.style.width = "200px";
        navContainer.style.display = "flex"
    } else {
        navContainer.style.width = "0px";
        navContainer.style.display = "none"
    }
}

function resizeSettingsInfo(id) {
    var info = document.getElementById(id);
    
    if (info.style.height === "0px" || info.style.height === "") {
        info.style.height = "100%";
        info.style.display = "block";
    } else {
        info.style.height = "0px";
        info.style.display = "none";
    }
}

function removeMessage() {
    var message = document.getElementsByClassName("message")[0];

    message.style.display = "none";
}