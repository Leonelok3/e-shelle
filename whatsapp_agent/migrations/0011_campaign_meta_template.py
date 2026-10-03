from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('whatsapp_agent', '0010_message_attachments')]
    operations = [
        migrations.AddField(model_name='campagne', name='template_meta_name', field=models.CharField(max_length=512, blank=True)),
        migrations.AddField(model_name='campagne', name='template_meta_language', field=models.CharField(max_length=20, blank=True)),
        migrations.AddField(model_name='campagne', name='template_meta_params', field=models.JSONField(default=list, blank=True)),
        migrations.AddField(model_name='campagne', name='template_meta_preview', field=models.TextField(blank=True)),
    ]
