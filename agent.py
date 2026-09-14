"""
AI Support Agent Core Pipeline for @AppleSupport
"""

import json
from intent_taxonomy import INTENT_TAXONOMY, check_mandatory_escalation

class SupportAgent:
    def __init__(self, use_llm_api: bool = False, api_key: str = None):
        self.use_llm_api = use_llm_api
        self.api_key = api_key
        self.taxonomy = INTENT_TAXONOMY

    def classify_intent(self, text: str) -> tuple[str, float]:
        """Classify incoming tweet into taxomic intents using semantic keyword weighting."""
        text_lower = text.lower()
        scores = {intent: 0 for intent in self.taxonomy}

        for intent, details in self.taxonomy.items():
            for kw in details["keywords"]:
                if kw in text_lower:
                    scores[intent] += 2 if len(kw) > 4 else 1

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        if max_score == 0:
            return "OTHER_GENERAL", 0.50

        confidence = min(0.95, 0.60 + (max_score * 0.10))
        return best_intent, confidence

    def generate_draft_reply(self, intent: str, customer_tweet: str, context: str = "") -> str:
        """Draft a reply grounded in historical @AppleSupport resolution patterns."""
        intent_info = self.taxonomy.get(intent, self.taxonomy["OTHER_GENERAL"])
        link = intent_info["knowledge_link"]

        if intent == "ACCOUNT_SECURITY":
            return f"Your account security is our top priority. Please verify your identity and reset your credentials securely at {link}."
        elif intent == "BILLING_SUBSCRIPTIONS":
            return f"We can help you investigate that charge! You can review your purchase history or request a refund at {link}."
        elif intent == "HARDWARE_REPAIR":
            return f"We know how important your device is! You can check official repair options, battery tips, and service pricing at {link}."
        elif intent == "SOFTWARE_UPDATE_BUG":
            return f"Thanks for letting us know! Try checking Settings > General > Software Update, or restart your device. Tips: {link}."
        elif intent == "DEVICE_TRADEIN_SHIPPING":
            return f"Let's look into your order status! Please send us a Direct Message with your order details so we can assist you safely."
        else:
            return f"Welcome to Apple Support! We're here to help. You can check our step-by-step guides and tips at {link}."

    def process_message(self, customer_tweet: str, context: str = "") -> dict:
        """Process customer message and produce structured decision output."""
        # Step 1: Classify Intent
        intent, confidence = self.classify_intent(customer_tweet)
        intent_config = self.taxonomy[intent]

        # Step 2: Check Mandatory Safety/Privacy Escalations
        mandatory_escalate, mandatory_reason = check_mandatory_escalation(customer_tweet)

        if mandatory_escalate:
            action = "ESCALATE"
            reason = mandatory_reason
        else:
            action = intent_config["default_action"]
            reason = intent_config["escalation_reason"]

        # Step 3: Draft Grounded Reply
        draft_reply = self.generate_draft_reply(intent, customer_tweet, context)

        return {
            "intent": intent,
            "confidence": round(confidence, 2),
            "draft_reply": draft_reply,
            "action": action,
            "reason": reason
        }

if __name__ == "__main__":
    agent = SupportAgent()
    sample = "@AppleSupport I see an unauthorized charge of $29.99 on my credit card. Help!"
    result = agent.process_message(sample)
    print(json.dumps(result, indent=2))
