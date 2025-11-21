# eligibility/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Program, Session, Answer
from .serializers import ProgramSerializer, SessionSerializer, AnswerSerializer
from .permissions import IsSubscriberOrReadOnly
from .services.scoring import score_program
from .services.rag import explain_with_citations
from .services.checklist import build_checklist

# 👇 ajoute ces imports pour la doc Swagger (facultatif mais utile)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Program.objects.filter(active=True).order_by("country","code")
    serializer_class = ProgramSerializer

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsSubscriberOrReadOnly]

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def answers(self, request, pk=None):
        session = self.get_object()
        payload = request.data or {}
        for k, v in payload.items():
            Answer.objects.update_or_create(session=session, key=k, defaults={"value_json": v})
        return Response({"ok": True})

    @extend_schema(
        parameters=[
            OpenApiParameter(name="country", description="Filtrer par pays (ex: Canada)", required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name="category", description="Filtrer par catégorie (study|work|pr)", required=False, type=OpenApiTypes.STR),
        ],
        request=SessionSerializer,  # Swagger affichera un body, mais tu peux l'envoyer vide
        responses={200: dict},
    )
    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        session = self.get_object()

        # 1) Reconstituer les réponses
        answers = {}
        for a in session.answers.all():
            ref = answers
            parts = a.key.split(".")
            for p in parts[:-1]:
                ref = ref.setdefault(p, {})
            ref[parts[-1]] = a.value_json

        # 2) Prendre country/category depuis la **query** OU le **body**
        country = request.query_params.get("country") or request.data.get("country")
        category = request.query_params.get("category") or request.data.get("category")

        # 3) Filtrer les programmes actifs
        q = Program.objects.filter(active=True)
        if country:
            q = q.filter(country=country)
        if category:
            q = q.filter(category=category)

        # 4) Scorer
        results = []
        for program in q:
            s = score_program(program, answers)
            s.update(explain_with_citations(program.code, program.country))
            s.update({"checklist": build_checklist(program)})
            results.append(s)
        results.sort(key=lambda x: (-int(x["eligible"]), -x["score"]))

        session.score_total = results[0]["score"] if results else 0
        session.result_json = {"answers": answers, "results": results}
        session.status = "completed"
        session.save()
        return Response(session.result_json)

    @action(detail=True, methods=["get"])
    def result(self, request, pk=None):
        session = self.get_object()
        return Response(session.result_json or {})

    @action(detail=True, methods=["get"])
    def checklist_pdf(self, request, pk=None):
        session = self.get_object()
        return Response({"pdf": "coming_soon", "result": session.result_json}, status=status.HTTP_200_OK)


