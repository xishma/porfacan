from .models import Page


def published_pages(request):
    pages = Page.objects.filter(is_published=True).only("title", "address")
    return {"site_pages": pages}
