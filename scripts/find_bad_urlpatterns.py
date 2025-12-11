# scripts/find_bad_urlpatterns.py
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

def inspect():
    try:
        import django
        django.setup()
        from django.urls import get_resolver, URLPattern, URLResolver
    except Exception as e:
        print("Erreur lors du setup Django:", e)
        raise

    resolver = get_resolver()
    bad = []

    def check(patterns, prefix=""):
        for i, p in enumerate(patterns):
            typ = type(p).__name__
            rep = repr(p)
            # URLPattern = simple path(), URLResolver = include()
            if not isinstance(p, (URLPattern, URLResolver)):
                bad.append((prefix, i, typ, rep))
            else:
                if isinstance(p, URLResolver):
                    try:
                        subs = p.url_patterns
                    except Exception as e:
                        subs = None
                    new_prefix = prefix + str(p.pattern)
                    if subs:
                        check(subs, new_prefix)

    try:
        root_patterns = resolver.url_patterns
    except Exception as e:
        print("Impossible de récupérer resolver.url_patterns:", e)
        root_patterns = []

    check(root_patterns, prefix="ROOT -> ")

    if not bad:
        print("✅ Aucun élément invalide trouvé dans urlpatterns.")
    else:
        print("❌ Éléments invalides trouvés :")
        for prefix, i, typ, rep in bad:
            print(f"- Sous {prefix}, position {i} → type={typ}, repr={rep}")

if __name__ == "__main__":
    inspect()
