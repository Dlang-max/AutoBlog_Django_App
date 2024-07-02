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
    
    if (navContainer.style.width === "0px") {
        navContainer.style.width = "200px";
        navContainer.style.border = "1px solid black"
    } else {
        navContainer.style.width = "0px";
        navContainer.style.border = "0px"
    }
}