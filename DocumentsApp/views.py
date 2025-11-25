from io import BytesIO

from django.http import FileResponse
from django.shortcuts import render
from django.contrib import messages

from .forms import TranslationForm, CompressionForm

# Librairies externes
from docx import Document
from deep_translator import GoogleTranslator
from pypdf import PdfReader, PdfWriter


def documents_home(request):
    """
    Page d'accueil du module Documents :
    2 boutons -> Traduction / Compression
    """
    return render(request, "DocumentsApp/home.html")


def translate_docx_file(uploaded_file, source_lang, target_lang):
    """
    Traduit un fichier .docx paragraphe par paragraphe
    sans toucher à la mise en forme (styles, gras, etc.).
    """
    uploaded_file.seek(0)
    buffer_in = BytesIO(uploaded_file.read())

    doc = Document(buffer_in)

    # Préparer le traducteur
    if source_lang == 'auto':
        translator = GoogleTranslator(source='auto', target=target_lang)
    else:
        translator = GoogleTranslator(source=source_lang, target=target_lang)

    # Paragraphes
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            text = run.text.strip()
            if text:
                run.text = translator.translate(text)

    # Tableaux (certificats, relevés, etc. sont souvent en tableaux)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        text = run.text.strip()
                        if text:
                            run.text = translator.translate(text)

    buffer_out = BytesIO()
    doc.save(buffer_out)
    buffer_out.seek(0)
    return buffer_out


def translation_view(request):
    """
    Vue : formulaire d’upload + téléchargement du document traduit.
    """
    if request.method == "POST":
        form = TranslationForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            source_lang = form.cleaned_data['source_lang']
            target_lang = form.cleaned_data['target_lang']

            # Vérifier l’extension
            if not uploaded_file.name.lower().endswith(".docx"):
                messages.error(request, "Seuls les fichiers .docx sont acceptés pour la traduction.")
            else:
                try:
                    translated_io = translate_docx_file(uploaded_file, source_lang, target_lang)

                    # Nom du fichier de sortie
                    base_name = uploaded_file.name.rsplit('.', 1)[0]
                    output_name = f"{base_name}_traduit_{target_lang}.docx"

                    return FileResponse(
                        translated_io,
                        as_attachment=True,
                        filename=output_name
                    )
                except Exception as e:
                    messages.error(request, f"Erreur lors de la traduction : {e}")
    else:
        form = TranslationForm()

    return render(request, "DocumentsApp/translation.html", {"form": form})


def compress_pdf_file(uploaded_file):
    """
    Re-écrit le PDF en essayant de réduire la taille.
    (Compression de base, sans réglages complexes.)
    """
    uploaded_file.seek(0)
    buffer_in = BytesIO(uploaded_file.read())
    reader = PdfReader(buffer_in)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(reader.metadata or {})

    buffer_out = BytesIO()
    writer.write(buffer_out)
    buffer_out.seek(0)
    return buffer_out


def compression_view(request):
    """
    Vue : upload PDF -> téléchargement PDF compressé.
    """
    if request.method == "POST":
        form = CompressionForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']

            if not uploaded_file.name.lower().endswith(".pdf"):
                messages.error(request, "Seuls les fichiers .pdf sont acceptés pour la compression.")
            else:
                try:
                    compressed_io = compress_pdf_file(uploaded_file)
                    base_name = uploaded_file.name.rsplit('.', 1)[0]
                    output_name = f"{base_name}_compressed.pdf"

                    return FileResponse(
                        compressed_io,
                        as_attachment=True,
                        filename=output_name
                    )
                except Exception as e:
                    messages.error(request, f"Erreur lors de la compression : {e}")
    else:
        form = CompressionForm()

    return render(request, "DocumentsApp/compression.html", {"form": form})
