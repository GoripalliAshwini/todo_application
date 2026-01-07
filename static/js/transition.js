document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll("a");

    links.forEach(link => {
        link.addEventListener("click", event => {
            const href = link.getAttribute("href");

            // Ignore external links
            if (!href || href.startsWith("http")) return;

            event.preventDefault();

            document.body.classList.add("fade-out");

            setTimeout(() => {
                window.location.href = href;
            }, 400); // match fadeOut duration
        });
    });
});
