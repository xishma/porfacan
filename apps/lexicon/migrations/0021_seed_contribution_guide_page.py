from django.db import migrations

CONTRIBUTION_GUIDE_PLACEHOLDER_CONTENT = """<h2>Contributing to the lexicon</h2>
<p>This page was created automatically. Replace this text in the admin with your community&rsquo;s contribution rules, style guide, and moderation expectations.</p>
<ul>
<li>Search for an existing headword before you suggest a new entry.</li>
<li>Write definitions in clear, neutral language; avoid insults, campaigning, and off-topic material.</li>
<li>Add examples and sources when they help readers verify or understand usage.</li>
<li>Respect copyright and privacy for links, images, and quotations.</li>
</ul>"""


def seed_contribution_guide_page(apps, schema_editor):
    Page = apps.get_model("lexicon", "Page")
    from django.conf import settings

    address = getattr(settings, "LEXICON_CONTRIBUTION_GUIDE_PAGE_ADDRESS", "contribute")
    if Page.objects.filter(address=address).exists():
        return
    Page.objects.create(
        address=address,
        title="Contribution guide",
        content=CONTRIBUTION_GUIDE_PLACEHOLDER_CONTENT,
        display_order=1,
        is_published=True,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0020_definition_usage_example_and_search_index"),
    ]

    operations = [
        migrations.RunPython(seed_contribution_guide_page, noop_reverse),
    ]
