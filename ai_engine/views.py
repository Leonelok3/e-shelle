"""
ai_engine/views.py — Vues IA E-Shelle
Génération de contenu, chat IA, streaming SSE.
"""
import json
from ai_engine.services.llm_service import stream_llm
from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import GenerationIA, TemplatePrompt


@login_required
def generateur(request):
    """Interface de génération de contenu IA."""
    templates = TemplatePrompt.objects.filter(actif=True).order_by("type_gen")
    return render(request, "ai_engine/generateur.html", {"templates": templates})


@csrf_exempt
@login_required
def stream_generate(request):
    """
    Endpoint SSE : génère du contenu IA en streaming via les fournisseurs OpenAI/Gemini.
    POST { prompt, type_gen, modele? }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST requis"}, status=405)

    try:
        data      = json.loads(request.body)
        prompt    = data.get("prompt", "").strip()
        type_gen  = data.get("type_gen", "contenu")
    except Exception:
        return JsonResponse({"error": "JSON invalide"}, status=400)

    if not prompt:
        return JsonResponse({"error": "Prompt vide"}, status=400)

    def event_stream():
        start = timezone.now()
        resultat_parts = []
        statut = "succes"
        usage = {"model": "", "input_tokens": 0, "output_tokens": 0}

        try:
            system = (
                "Tu es un assistant expert en création de contenu éducatif et marketing "
                "pour la plateforme E-Shelle, ciblant les entrepreneurs africains. "
                "Réponds en français, de façon claire et structurée."
            )
            for chunk in stream_llm(system, prompt, usage=usage, max_tokens=2048):
                resultat_parts.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception:
            statut = "erreur"
            yield f"data: {json.dumps({'error': 'Génération IA indisponible. Veuillez réessayer.'})}\n\n"

        # Sauvegarder la génération en base
        duree = int((timezone.now() - start).total_seconds() * 1000)
        GenerationIA.objects.create(
            utilisateur=request.user,
            type_gen=type_gen,
            modele=usage["model"],
            prompt=prompt[:2000],
            resultat="".join(resultat_parts)[:8000],
            tokens_input=usage["input_tokens"],
            tokens_output=usage["output_tokens"],
            statut=statut,
            duree_ms=duree,
        )
        yield f"data: {json.dumps({'done': True, 'tokens': usage['output_tokens']})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
def historique_ia(request):
    """Historique des générations IA de l'utilisateur."""
    generations = GenerationIA.objects.filter(
        utilisateur=request.user
    ).order_by("-created_at")[:50]
    return render(request, "ai_engine/historique.html", {"generations": generations})
