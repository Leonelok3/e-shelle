import csv

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import OCRError, extract_from_image


ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}


def dashboard(request):
    context = {
        "numbers": [],
        "whatsapp_numbers": [],
        "raw_text": "",
        "error": "",
    }
    if request.method == "POST":
        image = request.FILES.get("image")
        if not image:
            context["error"] = "Charge une capture d'ecran PNG ou JPG."
        elif image.content_type not in ALLOWED_CONTENT_TYPES:
            context["error"] = "Format refuse. Utilise PNG, JPG ou JPEG."
        else:
            try:
                result = extract_from_image(image)
                context["numbers"] = result.numbers
                context["whatsapp_numbers"] = result.whatsapp_numbers
                context["raw_text"] = result.text
            except OCRError as exc:
                context["error"] = str(exc)

    return render(request, "phone_ocr_agent/dashboard.html", context)


@require_POST
def export_csv(request):
    numbers = [line.strip() for line in request.POST.get("numbers", "").splitlines() if line.strip()]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="contacts-phone-ocr.csv"'
    writer = csv.writer(response)
    writer.writerow(["numero"])
    for number in numbers:
        writer.writerow([number])
    return response

# Create your views here.
