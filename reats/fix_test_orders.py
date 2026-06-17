import re

files = ["tests/customer_app/orders/create/test_api.py", "tests/customer_app/orders/update/test_api.py"]

for f in files:
    with open(f, "r") as file:
        content = file.read()

    # We want to insert "status": "draft" exactly before "stripe_payment_intent_id"
    # ONLY IF "status" is not already in the preceding lines of that dict block.

    # Let's just blindly replace `"stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw"`
    # where it is preceded by `"paid_date": None,` or `"ephemeral_key"`

    # Actually, a simpler regex:
    new_content = re.sub(
        r'([ \t]+)"stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",',
        r'\1"status": "draft",\n\1"stripe_payment_intent_id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",',
        content,
    )

    with open(f, "w") as file:
        file.write(new_content)

print("Done")
