"""
Redistribute correct_option across A/B/C/D for ce_B2_new21.json
by rotating the answer positions within each question so the correct
answer appears in positions A, B, C, D in a varied pattern.
"""
import json
import copy

with open('C:/Users/USER/OneDrive - IMAGENAF/Documents/immigration97/data/lessons_json/ce_B2_new21.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Define a target rotation pattern for the 4 questions in each lesson.
# Pattern: which position (0-indexed) the correct answer should land in (0=A,1=B,2=C,3=D)
# We cycle through different patterns to ensure variety across all 21 lessons.
# Each lesson has 4 questions. We assign target positions for each question.
LESSON_PATTERNS = [
    # lesson 1
    [0, 1, 2, 3],  # A B C D
    # lesson 2
    [2, 0, 3, 1],  # C A D B
    # lesson 3
    [1, 3, 0, 2],  # B D A C
    # lesson 4
    [3, 2, 1, 0],  # D C B A
    # lesson 5
    [0, 3, 1, 2],  # A D B C
    # lesson 6
    [2, 1, 3, 0],  # C B D A
    # lesson 7
    [1, 0, 2, 3],  # B A C D
    # lesson 8
    [3, 1, 0, 2],  # D B A C
    # lesson 9
    [0, 2, 3, 1],  # A C D B
    # lesson 10
    [2, 3, 0, 1],  # C D A B
    # lesson 11
    [1, 2, 3, 0],  # B C D A
    # lesson 12
    [3, 0, 2, 1],  # D A C B
    # lesson 13
    [0, 1, 3, 2],  # A B D C
    # lesson 14
    [2, 0, 1, 3],  # C A B D
    # lesson 15
    [1, 3, 2, 0],  # B D C A
    # lesson 16
    [3, 2, 0, 1],  # D C A B
    # lesson 17
    [0, 3, 2, 1],  # A D C B
    # lesson 18
    [2, 1, 0, 3],  # C B A D
    # lesson 19
    [1, 0, 3, 2],  # B A D C
    # lesson 20
    [3, 1, 2, 0],  # D B C A
    # lesson 21
    [0, 2, 1, 3],  # A C B D
]

LETTERS = ['A', 'B', 'C', 'D']
OPTION_KEYS = ['option_a', 'option_b', 'option_c', 'option_d']

def rotate_question(question, target_position):
    """
    Rotate the options of a question so the correct answer lands at target_position.
    Currently all correct answers are at position B (index 1).
    """
    # Find current correct position
    current_correct_letter = question['correct_option']
    current_pos = LETTERS.index(current_correct_letter)  # 0-indexed

    # Get current options in order
    current_options = [question[k] for k in OPTION_KEYS]

    # The correct answer value
    correct_value = current_options[current_pos]

    # We need to move correct answer from current_pos to target_position.
    # To do this, compute the rotation shift needed.
    # But we don't want to just rotate — we want the correct answer at target_position
    # while keeping the other options in a consistent shuffled order.
    # Strategy: build new options list by placing correct at target, then fill rest.

    other_options = [opt for i, opt in enumerate(current_options) if i != current_pos]

    new_options = [None] * 4
    new_options[target_position] = correct_value

    other_positions = [i for i in range(4) if i != target_position]
    for i, pos in enumerate(other_positions):
        new_options[pos] = other_options[i]

    new_question = copy.copy(question)
    for i, key in enumerate(OPTION_KEYS):
        new_question[key] = new_options[i]
    new_question['correct_option'] = LETTERS[target_position]

    return new_question

fixed_data = []
for lesson_idx, lesson in enumerate(data):
    pattern = LESSON_PATTERNS[lesson_idx]
    new_lesson = copy.copy(lesson)
    new_questions = []
    for q_idx, question in enumerate(lesson['questions']):
        target_pos = pattern[q_idx]
        new_q = rotate_question(question, target_pos)
        new_questions.append(new_q)
    new_lesson['questions'] = new_questions
    fixed_data.append(new_lesson)

# Save
with open('C:/Users/USER/OneDrive - IMAGENAF/Documents/immigration97/data/lessons_json/ce_B2_new21.json', 'w', encoding='utf-8') as f:
    json.dump(fixed_data, f, ensure_ascii=False, indent=2)

print("Saved. Verifying distribution:")
all_opts = []
for i, lesson in enumerate(fixed_data):
    opts = [q['correct_option'] for q in lesson['questions']]
    all_opts.extend(opts)
    print(f"  L{i+1}: {opts}")

from collections import Counter
print(f"\nDistribution: {Counter(all_opts)}")
print(f"Total questions: {len(all_opts)}")
