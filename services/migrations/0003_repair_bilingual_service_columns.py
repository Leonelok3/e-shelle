"""Répare les colonnes bilingues absentes malgré l'état de migration 0002."""
from django.db import migrations


FIELDS = {
    "OffreService": ("titre_en", "description_en", "features_en"),
    "CategoriePortfolio": ("nom_en",),
    "ProjetPortfolio": ("titre_en", "description_en"),
}


def ensure_columns_exist(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))

    for model_name, field_names in FIELDS.items():
        model = apps.get_model("services", model_name)
        table = model._meta.db_table
        if table not in existing_tables:
            continue
        with connection.cursor() as cursor:
            existing_columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }
        for field_name in field_names:
            field = model._meta.get_field(field_name)
            if field.column not in existing_columns:
                schema_editor.add_field(model, field)
                existing_columns.add(field.column)


class Migration(migrations.Migration):
    dependencies = [("services", "0002_bilingual_service_content")]

    operations = [migrations.RunPython(ensure_columns_exist, migrations.RunPython.noop)]
