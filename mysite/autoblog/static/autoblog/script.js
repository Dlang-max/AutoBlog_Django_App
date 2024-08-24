document.getElementById("blog-form").addEventListener("submit", () => {
    const title = document.getElementById("title").innerText;
    document.getElementById("id_title").value = title;

    const content = document.getElementById("quill-input-id_content").value;
    const parsedValue = JSON.parse(content);
    document.getElementById("id_content").value = parsedValue.html;
});


function removeMessage() {
    var message = document.getElementsByClassName("message")[0];

    message.style.display = "none";
}