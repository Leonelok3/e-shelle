from django.db import migrations


def disable_adgen_free_plan(apps, schema_editor):
    AppPlan = apps.get_model("accounts", "AppPlan")
    AppPlan.objects.filter(app_key="adgen", is_free=True).update(is_active=False)
    AppPlan.objects.filter(slug="adgen-free").update(is_active=False)


def restore_adgen_free_plan(apps, schema_editor):
    AppPlan = apps.get_model("accounts", "AppPlan")
    AppPlan.objects.filter(slug="adgen-free").update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_alter_appplan_app_key"),
    ]

    operations = [
        migrations.RunPython(disable_adgen_free_plan, restore_adgen_free_plan),
    ]
