"""
Training data for the intent classifier (see intent_classifier.py).

Every example under "seed" is a REAL message that actually caused a
routing bug during this project's development - pulled directly from
observed failures, not invented. Examples under "augmented" are
mechanical paraphrases/typo variations of those same real cases, added
so each class has enough examples to train on; they're kept separate
and clearly labeled so it's honest about what's real user data vs.
synthetic filler.

Labels correspond to existing Agent routing methods
(_looks_like_weather_request, _looks_like_document_request, etc.) -
the classifier is meant to catch what those regex/keyword checks miss
(typos, unfamiliar phrasing), not replace them outright. See
intent_classifier.py and agent.py's use of it in run().
"""

TRAINING_DATA = {
    "weather": {
        "seed": [
            "today weather",
            "today weathe",
            "ahmedabad today weather",
            "what is the weather today",
            "weather in Ahmedabad",
            "today waether ahemdabad",
        ],
        "augmented": [
            "what's the weather like today",
            "weather forecast for tomorrow",
            "is it going to rain today",
            "current temperature in mumbai",
            "how hot is it right now",
            "weather update please",
            "check the weather in delhi",
            "todays weather report",
            "whats the temperature outside",
            "give me the weather",
        ],
    },
    "document": {
        "seed": [
            "from pdf give me answer",
            "from pdf",
            "yes give me answer of 1 to 10 question in detail",
            "answer 1 qution",
            "from pdf ans 1 qutions",
            "yes, from pdf answer 1st question",
            "can you tell me how many credit of python from pdf",
            "it s on Sai Aman Zakirsha.pdf",
            "Discrete Mathematics, credits",
            "and,Fundamentals of Computer Science using Python - II",
            "Theory of Computation, credits",
            "total credits",
            "give me detail from this pdf",
        ],
        "augmented": [
            "what does the syllabus say about unit 3",
            "summarize the uploaded document",
            "explain question 5 from the file",
            "answer question number 2",
            "what are the credits for data structures",
            "from the document, what is covered in chapter 1",
            "based on the file, list the topics",
            "according to the pdf what books are recommended",
            "explain the second question in detail",
            "what's on page 3 of the syllabus",
        ],
    },
    "code": {
        "seed": [
            "code for adding tow numbers",
        ],
        "augmented": [
            "write a function that reverses a string",
            "write python code to check if a number is prime",
            "debug this code for me",
            "create a script that sorts a list",
            "write a program to calculate factorial",
            "fix the bug in my function",
            "generate code for a binary search",
            "write a class for a stack",
            "code to read a csv file",
            "write a function to check palindrome",
        ],
    },
    "search": {
        "seed": [
            "todsy football match",
            "fifa match",
            "today football match",
            "web search and give me top best place in india",
        ],
        "augmented": [
            "who is the current ceo of openai",
            "latest news on ai",
            "what's the score of the match today",
            "who won the game last night",
            "search for best laptops 2026",
            "top 10 movies this year",
            "current stock price of tesla",
            "live cricket score",
            "who is the prime minister right now",
            "breaking news today",
        ],
    },
    "datetime": {
        "seed": [
            "today date",
            "todsy date",
        ],
        "augmented": [
            "what's today's date",
            "what day is it",
            "what time is it",
            "current date please",
            "tell me the date today",
            "what's the current time",
            "what year is it",
        ],
    },
    "open": {
        "seed": [
            "open google",
            "open vs code",
            "open file D:\\Sem3",
        ],
        "augmented": [
            "open youtube",
            "launch vscode",
            "start notepad",
            "open chrome",
            "launch the calculator",
            "open my downloads folder",
            "start spotify",
            "open whatsapp",
            "launch file explorer",
            "open D:\\Projects\\report.docx",
        ],
    },
    "chat": {
        "seed": [
            "hii",
            "what is my name",
        ],
        "augmented": [
            "hello",
            "hey there",
            "how are you",
            "good morning",
            "thanks",
            "who are you",
            "what can you do",
            "tell me a joke",
            "how's it going",
            "nice to meet you",
        ],
    },
    "math": {
        "seed": [
            "add 10 and 20",
        ],
        "augmented": [
            "multiply 5 and 2",
            "subtract 10 from 30",
            "divide 100 by 4",
            "what is 15 plus 27",
            "what's 8 times 9",
            "calculate 45 minus 12",
            "add 3, 4 and 5",
            "what is 200 divided by 5",
            "sum of 10 and 15",
            "what's 12 multiplied by 3",
        ],
    },
}


def get_training_examples(include_augmented=True):
    """
    Flatten TRAINING_DATA into (text, label) pairs for training.
    Set include_augmented=False to train/evaluate on only the real,
    observed examples (useful for an honest sanity check of how well
    this generalizes from real data alone, before synthetic filler).
    """
    examples = []
    for label, groups in TRAINING_DATA.items():
        examples.extend((text, label) for text in groups["seed"])
        if include_augmented:
            examples.extend((text, label) for text in groups["augmented"])
    return examples


LABELS = sorted(TRAINING_DATA.keys())
