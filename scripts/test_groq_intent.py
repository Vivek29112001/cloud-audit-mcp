from app.ai.groq_client import (
    GroqIntentClient,
)


client = GroqIntentClient()

intent = client.parse_aws_question(
    "show all ec2 instances"
)

print(
    intent.model_dump(
        mode="json"
    )
)

print(
    "PARAMS:",
    intent.get_params()
)