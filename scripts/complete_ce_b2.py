import re
import json

# Read the partial file
with open('C:/Users/USER/OneDrive - IMAGENAF/Documents/immigration97/data/lessons_json/ce_B2_new21.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Find position after lesson 18 (72 summaries = 18 lessons x 4 questions each)
summaries = list(re.finditer(r'"summary":', content))
last_summary_pos = summaries[-1].start()
after = content[last_summary_pos:]
match = re.search(r'"\s*\n\s*\}\s*\n\s*\]\s*\n\s*\}', after)
cut_pos = last_summary_pos + match.end()
good_content = content[:cut_pos]

lessons_to_add = [
    {
        "title": "La santé mentale des travailleurs immigrants : enjeux et ressources",
        "reading_text": "<p>La migration est un processus profondément transformateur qui peut engendrer des <strong>crises identitaires</strong>, des deuils multiples — rupture avec le pays d'origine, perte du statut social, éloignement de la famille — et des états de stress prolongé qui, sans soutien adéquat, peuvent évoluer vers des troubles psychologiques sérieux. Pourtant, la santé mentale des travailleurs immigrants reste un angle mort des politiques publiques québécoises.<br><br>Des études montrent que les immigrants récents présentent souvent, dans un premier temps, de meilleurs indicateurs de santé que la population native — un phénomène connu sous le nom de <strong>paradoxe de l'immigrant en bonne santé</strong>. Cette tendance s'érode cependant rapidement avec le temps d'exposition aux conditions de précarité, de discrimination et d'isolement social qui caractérisent fréquemment les premières années d'installation. Au bout de quelques années, les immigrants présentent des taux de dépression, d'anxiété et de troubles post-traumatiques équivalents ou supérieurs à ceux de la population générale.<br><br>L'accès aux services de santé mentale est lui-même semé d'obstacles pour les immigrants : barrières linguistiques, méconnaissance des ressources disponibles, coût des services privés lorsque la RAMQ ne couvre pas certains soins, et <strong>stigmatisation culturelle</strong> de la santé mentale dans de nombreuses communautés d'origine. Des cultures valorisent la résilience et le silence face à la souffrance psychologique, rendant la demande d'aide difficile.<br><br>Des organismes comme <strong>PRAIDA</strong> à Montréal offrent des services intégrés aux demandeurs d'asile, et certains CLSC ont développé des équipes multiculturelles. Mais l'offre reste insuffisante, fragmentée et souvent peu connue des personnes qui en auraient le plus besoin. Une approche systémique, intégrant la santé mentale dans tous les programmes d'accueil des immigrants, est réclamée par les professionnels du secteur.</p>",
        "questions": [
            {
                "question_text": "Que désigne le paradoxe de l'immigrant en bonne santé selon le texte ?",
                "option_a": "Le fait que les immigrants ont accès à de meilleurs soins de santé que les Québécois natifs",
                "option_b": "Le phénomène par lequel les immigrants récents présentent de meilleurs indicateurs de santé que la population native, avant que cette tendance s'érode",
                "option_c": "La résilience psychologique exceptionnelle que développent les immigrants face à l'adversité",
                "option_d": "Le fait que les immigrants sont moins susceptibles de développer des maladies chroniques",
                "correct_option": "B",
                "summary": "Le texte définit le paradoxe de l'immigrant en bonne santé comme le phénomène par lequel les immigrants récents présentent de meilleurs indicateurs de santé, une tendance qui s'érode avec le temps."
            },
            {
                "question_text": "Quels obstacles freinent l'accès des immigrants aux services de santé mentale selon le texte ?",
                "option_a": "Le manque de psychiatres formés aux réalités interculturelles et les listes d'attente trop longues",
                "option_b": "Les barrières linguistiques, la méconnaissance des ressources, le coût des services privés et la stigmatisation culturelle",
                "option_c": "La discrimination des professionnels de santé envers les patients immigrants",
                "option_d": "L'absence de couverture par la RAMQ pour tous les immigrants durant la première année",
                "correct_option": "B",
                "summary": "Le texte identifie comme obstacles les barrières linguistiques, la méconnaissance des ressources, le coût des services privés et la stigmatisation culturelle."
            },
            {
                "question_text": "Que fait l'organisme PRAIDA à Montréal selon le texte ?",
                "option_a": "Il assure la représentation juridique gratuite des demandeurs d'asile devant les tribunaux d'immigration",
                "option_b": "Il offre des services intégrés aux demandeurs d'asile, notamment en matière de santé mentale",
                "option_c": "Il gère un réseau de familles d'accueil pour les demandeurs d'asile",
                "option_d": "Il coordonne les programmes de francisation destinés aux demandeurs d'asile",
                "correct_option": "B",
                "summary": "Le texte précise que PRAIDA offre des services intégrés aux demandeurs d'asile à Montréal."
            },
            {
                "question_text": "Quelle évolution le texte observe-t-il dans les taux de troubles mentaux des immigrants avec le temps ?",
                "option_a": "Les immigrants développent progressivement une immunité psychologique au stress migratoire",
                "option_b": "Les taux de dépression, d'anxiété et de troubles post-traumatiques deviennent équivalents ou supérieurs à ceux de la population générale",
                "option_c": "Les immigrants retournent dans leur pays d'origine avant que les troubles ne deviennent sérieux",
                "option_d": "Les immigrants de deuxième génération bénéficient des mêmes avantages de santé que leurs parents",
                "correct_option": "B",
                "summary": "Le texte indique qu'après quelques années, les immigrants présentent des taux de dépression, d'anxiété et de troubles post-traumatiques équivalents ou supérieurs à ceux de la population générale."
            }
        ]
    },
    {
        "title": "L'endettement étudiant et l'accès aux études supérieures",
        "reading_text": "<p>Au Québec, les droits de scolarité universitaires sont parmi les plus bas en Amérique du Nord pour les résidents québécois, grâce à un système de régulation tarifaire défendu bec et ongles par des générations d'étudiants — notamment lors du célèbre <strong>Printemps érable de 2012</strong>. Cette accessibilité financière relative est souvent présentée comme un pilier de l'égalité des chances et un atout pour attirer des immigrants qualifiés souhaitant se former ou compléter leurs études au Québec.<br><br>Cependant, la réalité est plus nuancée. Les étudiants immigrants ne bénéficient pas des mêmes tarifs que les résidents québécois : les <strong>étudiants internationaux</strong> paient des droits de scolarité plusieurs fois supérieurs, pouvant atteindre 30 000 dollars par année dans certains programmes. Même pour les résidents permanents récents, la qualification aux tarifs résidents peut nécessiter une période d'attente. Cette structure tarifaire différenciée crée des inégalités d'accès significatives entre étudiants locaux et internationaux.<br><br>Par ailleurs, même pour les étudiants québécois, l'endettement étudiant constitue un enjeu croissant. Les prêts et bourses du gouvernement provincial ne couvrent pas toujours l'intégralité des coûts de vie, contraignant les étudiants à travailler de nombreuses heures pendant leurs études, ce qui peut nuire à leur réussite académique. Les étudiants immigrants, qui ne bénéficient pas toujours du soutien familial disponible pour les étudiants natifs, sont particulièrement exposés à cette pression financière.<br><br>Des voix s'élèvent pour réformer le système : certains plaident pour une <strong>gratuité scolaire</strong> universelle jusqu'à un certain niveau d'études, d'autres pour des prêts à remboursement conditionnel au revenu — un modèle appliqué avec succès en Australie et au Royaume-Uni. La question de l'accessibilité aux études supérieures pour les immigrants reste un enjeu fondamental d'équité sociale et d'intégration réussie.</p>",
        "questions": [
            {
                "question_text": "Quel événement de 2012 est associé à la défense des droits de scolarité bas au Québec ?",
                "option_a": "La grève générale des enseignants universitaires québécois",
                "option_b": "Le Printemps érable",
                "option_c": "La Grande marche pour l'éducation de Montréal",
                "option_d": "Le Référendum étudiant sur la gratuité scolaire",
                "correct_option": "B",
                "summary": "Le texte mentionne le Printemps érable de 2012 comme l'événement emblématique associé à la défense des droits de scolarité bas au Québec."
            },
            {
                "question_text": "Combien les étudiants internationaux peuvent-ils payer en droits de scolarité annuels selon le texte ?",
                "option_a": "Jusqu'à 10 000 dollars par année",
                "option_b": "Jusqu'à 30 000 dollars par année dans certains programmes",
                "option_c": "Jusqu'à 50 000 dollars par année dans les programmes professionnels",
                "option_d": "Jusqu'à 15 000 dollars par année, soit deux fois le tarif résident",
                "correct_option": "B",
                "summary": "Le texte précise que les étudiants internationaux peuvent payer jusqu'à 30 000 dollars par année dans certains programmes."
            },
            {
                "question_text": "Quel problème les prêts et bourses du gouvernement provincial posent-ils selon le texte ?",
                "option_a": "Ils sont remboursables à des taux d'intérêt trop élevés qui endettent les diplômés pour des décennies",
                "option_b": "Ils ne couvrent pas toujours l'intégralité des coûts de vie, forçant les étudiants à travailler pendant leurs études",
                "option_c": "Ils sont inaccessibles aux étudiants immigrants qui ne peuvent pas y cotiser",
                "option_d": "Ils créent une dépendance à l'aide gouvernementale qui nuit à l'autonomie des étudiants",
                "correct_option": "B",
                "summary": "Le texte indique que les prêts et bourses ne couvrent pas toujours l'intégralité des coûts de vie, contraignant les étudiants à travailler et nuisant à leur réussite académique."
            },
            {
                "question_text": "Quel modèle de remboursement de prêts étudiants est cité comme exemple de bonne pratique internationale ?",
                "option_a": "Le modèle américain de prêts subventionnés avec période de grâce de cinq ans",
                "option_b": "Le modèle australien et britannique de prêts à remboursement conditionnel au revenu",
                "option_c": "Le modèle nordique de gratuité totale financée par une taxe sur les entreprises",
                "option_d": "Le modèle allemand de prêts à taux zéro remboursables sur trente ans",
                "correct_option": "B",
                "summary": "Le texte cite l'Australie et le Royaume-Uni comme exemples de pays ayant appliqué avec succès un modèle de prêts à remboursement conditionnel au revenu."
            }
        ]
    },
    {
        "title": "Les droits des réfugiés au Canada selon la Convention de Genève",
        "reading_text": "<p>Le Canada est signataire de la <strong>Convention relative au statut des réfugiés</strong>, adoptée à Genève en 1951 et complétée par le Protocole de 1967. Ce cadre juridique international définit qui peut être reconnu comme réfugié et quelles protections les États signataires sont tenus d'offrir. Selon cette convention, un réfugié est une personne qui craint avec raison d'être persécutée en raison de sa race, de sa religion, de sa nationalité, de son appartenance à un groupe social particulier ou de ses opinions politiques.<br><br>Au Canada, les demandes d'asile sont instruites par la <strong>Commission de l'immigration et du statut de réfugié (CISR)</strong>, un tribunal administratif indépendant. Le processus comprend généralement une audience devant un commissaire qui évalue la crédibilité du demandeur et le risque réel auquel il serait exposé en cas de retour dans son pays d'origine. Les délais de traitement, qui peuvent atteindre plusieurs années, plongent les demandeurs dans une <strong>longue période d'incertitude</strong> administrative, sociale et psychologique.<br><br>Les droits reconnus aux demandeurs d'asile pendant l'attente sont limités mais réels : droit de travailler après un certain délai, accès aux soins de santé via le <strong>Programme fédéral de santé intérimaire</strong>, et accès à l'éducation pour les enfants. Ceux dont la demande est acceptée obtiennent la résidence permanente et peuvent à terme demander la citoyenneté. Ceux dont la demande est refusée peuvent faire appel, mais risquent en dernier recours d'être expulsés.<br><br>Des enjeux contemporains viennent complexifier ce système : l'afflux de demandeurs d'asile via des passages irréguliers comme le chemin Roxham, les accords de tiers pays sûrs, et la montée des discours politiques qui assimilent réfugiés et migrants économiques, contribuant à une stigmatisation qui rend encore plus difficile l'intégration de ceux dont la protection a pourtant été légalement reconnue.</p>",
        "questions": [
            {
                "question_text": "Selon la Convention de Genève rappelée dans le texte, sur quels critères une personne peut-elle être reconnue réfugiée ?",
                "option_a": "Sur la base d'une catastrophe naturelle ou d'une crise économique grave dans son pays d'origine",
                "option_b": "Sur la base d'une crainte fondée de persécution liée à la race, la religion, la nationalité, l'appartenance à un groupe social ou les opinions politiques",
                "option_c": "Sur la base d'un conflit armé international ayant déplacé au moins un million de personnes",
                "option_d": "Sur la base d'une demande appuyée par un État tiers qui garantit la véracité de la persécution",
                "correct_option": "B",
                "summary": "La Convention de Genève définit le réfugié comme une personne craignant d'être persécutée en raison de sa race, religion, nationalité, appartenance à un groupe social ou opinions politiques."
            },
            {
                "question_text": "Quel organisme instruit les demandes d'asile au Canada selon le texte ?",
                "option_a": "Le ministère de l'Immigration, des Réfugiés et de la Citoyenneté du Canada",
                "option_b": "La Commission de l'immigration et du statut de réfugié (CISR)",
                "option_c": "Le Haut-Commissariat des Nations Unies pour les réfugiés (HCR)",
                "option_d": "La Cour fédérale du Canada, chambre de l'immigration",
                "correct_option": "B",
                "summary": "Le texte précise que les demandes d'asile sont instruites par la Commission de l'immigration et du statut de réfugié (CISR), un tribunal administratif indépendant."
            },
            {
                "question_text": "Quel droit les demandeurs d'asile ont-ils en matière d'accès aux soins de santé selon le texte ?",
                "option_a": "Ils ont accès au système de santé provincial dès le premier jour de leur arrivée au Canada",
                "option_b": "Ils ont accès aux soins via le Programme fédéral de santé intérimaire",
                "option_c": "Ils doivent souscrire à une assurance privée jusqu'à l'obtention de leur résidence permanente",
                "option_d": "Ils n'ont accès qu'aux soins d'urgence dans les hôpitaux publics canadiens",
                "correct_option": "B",
                "summary": "Le texte indique que les demandeurs d'asile ont accès aux soins de santé via le Programme fédéral de santé intérimaire."
            },
            {
                "question_text": "Quel phénomène le texte identifie-t-il comme complexifiant le système d'asile canadien ?",
                "option_a": "La saturation des ressources humaines de la CISR qui allonge les délais de traitement",
                "option_b": "La montée des discours politiques qui assimilent réfugiés et migrants économiques, contribuant à leur stigmatisation",
                "option_c": "Le refus croissant d'autres pays signataires de respecter la Convention de Genève",
                "option_d": "L'augmentation du nombre de fausses demandes d'asile qui fragilisent la crédibilité du système",
                "correct_option": "B",
                "summary": "Le texte identifie la montée des discours politiques assimilant réfugiés et migrants économiques comme un facteur complexifiant, contribuant à leur stigmatisation."
            }
        ]
    }
]

# Build final JSON: good_content (18 lessons) + comma + 3 more lessons + close array
# good_content ends with "  }" (lesson 18 closing)
# We need to add ",\n" then each new lesson serialized, then close with "\n]"

import json

# Serialize the new lessons
new_lessons_json = json.dumps(lessons_to_add, ensure_ascii=False, indent=2)
# new_lessons_json starts with "[" and ends with "]"
# We want to extract the individual lesson objects
# They are separated by commas in the array - let's extract them one by one

# Actually easier: serialize each individually
lesson_strings = []
for lesson in lessons_to_add:
    s = json.dumps(lesson, ensure_ascii=False, indent=2)
    # Indent by 2 more spaces to match existing format
    lines = s.split('\n')
    indented = '\n'.join('  ' + line for line in lines)
    lesson_strings.append(indented)

addition = ',\n' + ',\n'.join(lesson_strings) + '\n]'

final_content = good_content + addition

with open('C:/Users/USER/OneDrive - IMAGENAF/Documents/immigration97/data/lessons_json/ce_B2_new21.json', 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"Written {len(final_content)} bytes")

# Validate
with open('C:/Users/USER/OneDrive - IMAGENAF/Documents/immigration97/data/lessons_json/ce_B2_new21.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Valid JSON! Number of lessons: {len(data)}")
for i, lesson in enumerate(data):
    print(f"  Lesson {i+1}: '{lesson['title']}' - {len(lesson['questions'])} questions - correct options: {[q['correct_option'] for q in lesson['questions']]}")
