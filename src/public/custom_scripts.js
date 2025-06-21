function addLogoClickHandler(img) {
  if (img.classList.contains("w-[150px]")) {
    img.style.cursor = "pointer";
    addRedirectToHomepage(img);
  }
}

function addRedirectToHomepage(element) {
  element.addEventListener("click", function () {
    window.location.href = "/";
  });
}

// This script adds a click handler to logo images that redirects to the homepage
// when clicked. It also observes the document for any new logo images added dynamically.

// Warning: This script assumes that the logo in this form is only presented when logging out
document.addEventListener("DOMContentLoaded", function () {
  // Check if the image is already present
  document.querySelectorAll("img.logo").forEach(addLogoClickHandler);

  // Add click handler to h1 > span with specific text
  document.querySelectorAll("h1 > span").forEach(function (span) {
    if (span.textContent.trim() === "Login to access the app") {
      const h1 = span.closest("h1");
      if (h1) {
        h1.style.cursor = "pointer";
        addRedirectToHomepage(h1);
      }
    }
  });

  // Improved MutationObserver: check all descendants for images and h1 > span
  const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) {
        if (node.nodeType === 1) {
          // If the node itself is an img.logo
          if (node.matches("img.logo")) {
            addLogoClickHandler(node);
          }
          // If the node contains any img.logo descendants
          node.querySelectorAll &&
            node.querySelectorAll("img.logo").forEach(addLogoClickHandler);

          // If the node itself is h1 > span with the text
          if (
            node.matches("h1 > span") &&
            node.textContent.trim() === "Login to access the app"
          ) {
            const h1 = node.closest("h1");
            if (h1) {
              h1.style.cursor = "pointer";
              addRedirectToHomepage(h1);
            }
          }
          // If the node contains any h1 > span descendants with the text
          node.querySelectorAll &&
            node.querySelectorAll("h1 > span").forEach(function (span) {
              if (span.textContent.trim() === "Login to access the app") {
                const h1 = span.closest("h1");
                if (h1) {
                  h1.style.cursor = "pointer";
                  addRedirectToHomepage(h1);
                  span.textContent = "Please log in again to access the app";

                  // Add a button beneath the login text that redirects to "/"
                  if (!h1.querySelector("button")) {
                    const btn = document.createElement("button");
                    btn.textContent = "Sign In";
                    btn.className =
                      "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg]:size-4 [&amp;_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full";
                    btn.style.display = "block";
                    btn.style.marginTop = "1em";
                    btn.addEventListener("click", function (e) {
                      e.stopPropagation();
                      window.location.href = "/";
                    });
                    h1.appendChild(btn);
                  }
                }
              }
            });
        }
      });
    });
  });

  observer.observe(document.body, { childList: true, subtree: true });
});
