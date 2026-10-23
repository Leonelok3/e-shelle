from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facebook_agent", "0002_alter_contentrule_section_alter_posttemplate_section_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scheduledpost",
            name="link_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="URL du lien"),
        ),
        migrations.AlterField(
            model_name="publishedpost",
            name="link_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
