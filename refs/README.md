# Inspiration photos (test input)

Drop garment inspiration photos here (`.jpg`, `.jpeg`, `.png`, `.webp`) to feed
the Designer agent:

    ./.venv/bin/python scripts/run_designer.py \
        --notes "your design clarifications" \
        --image refs/your-photo.jpg \
        --sizes S M L XL --garment shirt

Image files in this folder are git-ignored (they may be proprietary). For best
results: a clear, well-lit photo of the whole garment, plain background.
