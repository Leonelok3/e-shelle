from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("germany_opportunities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="useropportunitybookmark",
            name="user",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="opportunity_bookmarks",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name="useropportunitybookmark",
            unique_together={("user", "offer"), ("user", "scholarship")},
        ),
    ]
