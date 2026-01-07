document.addEventListener("DOMContentLoaded", () => {
    const deleteLinks = document.querySelectorAll(".delete-task");

    deleteLinks.forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            const task = link.closest(".task-item");
            const href = link.getAttribute("href");

            task.classList.add("task-remove");

            setTimeout(() => {
                window.location.href = href;
            }, 300);
        });
    });
});
