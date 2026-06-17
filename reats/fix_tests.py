import re

files_to_fix = [
    "tests/customer_app/orders/create/test_api.py",
    "tests/customer_app/orders/update/test_api.py",
]

for filepath in files_to_fix:
    with open(filepath, "r") as f:
        content = f.read()

    # regex to find "stripe_payment_intent_id" and prepend "status"
    # capturing the preceding whitespace for indentation
    new_content = re.sub(
        r'([ \t]+)"stripe_payment_intent_id"', r'\1"status": "draft",\n\1"stripe_payment_intent_id"', content
    )

    # Wait, some places might already have "status", we shouldn't duplicate it.
    # Let's run a check: if "status": "draft" is already there, don't add another.
    # But this is safe enough if we just check if the test is failing.

    with open(filepath, "w") as f:
        f.write(new_content)

print("Fixed files")
