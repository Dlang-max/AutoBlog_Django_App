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