from __future__ import annotations

import re


class ChatTitleService:
    MAX_LENGTH = 60

    PREFIXES = (
        "show me ",
        "show ",
        "list ",
        "get ",
        "tell me ",
        "which ",
        "what are ",
        "what is ",
        "can you show ",
    )

    AWS_TERMS = {
        "Ec2": "EC2",
        "Rds": "RDS",
        "Iam": "IAM",
        "Aws": "AWS",
        "S3": "S3",
        "Eks": "EKS",
        "Ecs": "ECS",
        "Vpc": "VPC",
        "Vpcs": "VPCs",
        "Dynamodb": "DynamoDB",
    }

    def generate(self, question: str) -> str:
        value = " ".join(question.strip().split())

        if not value:
            return "New AWS Chat"

        lower = value.lower()

        for prefix in self.PREFIXES:
            if lower.startswith(prefix):
                value = value[len(prefix):].strip()
                break

        value = re.sub(r"[?!.]+$", "", value)

        if not value:
            return "New AWS Chat"

        value = value[:self.MAX_LENGTH].strip().title()

        return " ".join(
            self.AWS_TERMS.get(word, word)
            for word in value.split()
        )
