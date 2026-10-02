"""Listening documents are distinct from instructions and teaching notes."""
import html
import re
import unicodedata
from django.utils.html import strip_tags


def spoken_text(value):
    value = re.sub(r"<\s*br\s*/?>|</(?:p|div|li|h[1-6])>", "\n", value or "", flags=re.I)
    return unicodedata.normalize("NFC", html.unescape(strip_tags(value))).strip()


def listening_script(exercise):
    """Only explicit documents or known legacy transcription markers are safe."""
    if exercise.lesson.section != "co":
        return ""
    if exercise.document_text.strip():
        return spoken_text(exercise.document_text)
    instruction = (exercise.instruction or "").strip()
    for marker in ("Audio indisponible. Travaillez sur cette transcription :",
                   "Transcription :", "Transcription de l'audio :"):
        if instruction.startswith(marker):
            return spoken_text(instruction[len(marker):])
    match = re.match(r"^Script d['’](?:ecoute|écoute) \([^\n]+?\):\s*(.+)$", instruction, re.S)
    if match:
        return spoken_text(match.group(1))
    return ""


def text_flags(value):
    if "\ufffd" in (value or "") or any(token in (value or "") for token in ("Ã©", "Ã¨", "Ã§", "â€™", "Â ")):
        return ["encoding_to_review"]
    return []


def repair_encoding(value):
    """Repair exact UTF-8 mojibake sequences, without guessing French spelling."""
    value = value or ""
    replacements = {}
    for character in "àâäéèêëîïôöùûüÿçœÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇŒ’‘“”–—… ":
        for encoding in ("latin1", "cp1252"):
            try:
                broken = character.encode("utf-8").decode(encoding)
            except UnicodeError:
                continue
            replacements[broken] = character
    for _ in range(2):
        previous = value
        for broken, character in sorted(replacements.items(), key=lambda pair: -len(pair[0])):
            value = value.replace(broken, character)
        if value == previous:
            break
    return value


# Editorial corrections confined to the known deterministic demonstration seed.
SEED_ACCENTS = dict(pair.split(":") for pair in (
    "teletravail:télétravail integration:intégration mobilite:mobilité sante:santé numeriques:numériques "
    "regional:régional benevolat:bénévolat reseautage:réseautage securite:sécurité diplomes:diplômes "
    "ecologique:écologique universites:universités appliquee:appliquée prevention:prévention donnees:données "
    "mediation:médiation qualifie:qualifié productivite:productivité democratique:démocratique ethique:éthique "
    "souverainete:souveraineté memoire:mémoire geopolitique:géopolitique epistemologie:épistémologie "
    "regulation:régulation economique:économique responsabilite:responsabilité ecoute:écoute repere:repère "
    "memoriser:mémoriser consequence:conséquence annoncee:annoncée ecrite:écrite reponse:réponse "
    "these:thèse developpes:développés precise:précise developpe:développe fluidite:fluidité methode:méthode "
    "cles:clés piege:piège evaluation:évaluation precision:précision coherence:cohérence theme:thème "
    "reunion:réunion dependra:dépendra capacite:capacité meme:même entree:entrée reconnait:reconnaît "
    "couts:coûts couteuse:coûteuse experience:expérience etudiante:étudiante difficulte:difficulté "
    "necessite:nécessité inference:inférence idee:idée presente:présente decision:décision depend:dépend evoquee:évoquée "
    "exprimees:exprimées enquete:enquête recente:récente reforme:réforme accompagnee:accompagnée "
    "concretes:concrètes realiste:réaliste mecanisme:mécanisme general:général element:élément reserves:réserves "
    "complete:complète interet:intérêt conseillee:conseillée evaluer:évaluer clarte:clarté developper:développer "
    "preparation:préparation facon:façon structuree:structurée ignore:ignoré lecons:leçons creees:créées "
    "crees:créés".split()
))


def repair_seed_text(value):
    def accented(match):
        word = match.group(0)
        replacement = SEED_ACCENTS.get(word.casefold())
        if replacement is None:
            return word
        return replacement.upper() if word.isupper() else replacement.capitalize() if word[0].isupper() else replacement
    value = re.sub(r"\b[A-Za-z]+\b", accented, value or "")
    for before, after in (("pas a tout", "pas à tout"), ("capacite a", "capacité à"),
                          ("capacité a", "capacité à"), ("couteuse a long", "coûteuse à long"),
                          ("coûteuse a long", "coûteuse à long"), (", a condition", ", à condition"),
                          ("se limite a", "se limite à"), ("mise en oeuvre", "mise en œuvre")):
        value = value.replace(before, after)
    return re.sub(r"(\d+) a (\d+)", r"\1 à \2", value)


def seed_listening_explanation(script):
    return (
        f"Indice dans le document : « {script} »\n"
        "B est correcte : le propos introduit une condition, une réserve ou une opposition. "
        "A est incorrecte : elle efface la difficulté ou la contrainte exprimée. "
        "C est incorrecte : une réserve ne constitue pas un rejet total. "
        "D est incorrecte : le locuteur exprime un jugement et ne donne pas seulement une information administrative."
    )
