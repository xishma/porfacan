(function () {
    const setEditorDirection = (editor) => {
        const view = editor.editing.view;
        view.change((writer) => {
            const root = view.document.getRoot();
            writer.setAttribute("dir", "rtl", root);
            writer.setStyle("text-align", "right", root);
        });
    };

    const init = () => {
        if (typeof window.ClassicEditor === "undefined") {
            return;
        }

        document.querySelectorAll("textarea.js-page-wysiwyg").forEach((textarea) => {
            if (textarea.dataset.wysiwygInitialized === "true") {
                return;
            }
            window.ClassicEditor.create(textarea, {
                language: {
                    ui: "fa",
                    content: "fa",
                },
            })
                .then((editor) => {
                    setEditorDirection(editor);
                })
                .catch(() => {
                    // Keep plain textarea fallback if editor loading fails.
                });
            textarea.dataset.wysiwygInitialized = "true";
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
        return;
    }
    init();
})();
