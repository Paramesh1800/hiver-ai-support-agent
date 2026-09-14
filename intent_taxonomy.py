"""
Intent Taxonomy and Escalation Rules for @AppleSupport AI Agent
"""

INTENT_TAXONOMY = {
    "ACCOUNT_SECURITY": {
        "description": "Apple ID lockouts, 2FA issues, password resets, suspicious logins, or compromised accounts.",
        "keywords": ["apple id", "password", "locked", "disabled", "compromised", "hacked", "2fa", "verification code", "login"],
        "default_action": "ESCALATE",
        "escalation_reason": "Account security and password resets involve sensitive user credentials and must be authenticated on secure Apple web portals.",
        "knowledge_link": "https://iforgot.apple.com"
    },
    "BILLING_SUBSCRIPTIONS": {
        "description": "Unrecognized App Store charges, refund requests, subscription cancellations, or payment method failures.",
        "keywords": ["charge", "refund", "billing", "subscription", "app store", "purchase", "card", "receipt", "unauthorized"],
        "default_action": "ESCALATE",
        "escalation_reason": "Refund requests and payment investigations require authenticated user session on reportaproblem.apple.com.",
        "knowledge_link": "https://reportaproblem.apple.com"
    },
    "HARDWARE_REPAIR": {
        "description": "Physical damage, screen replacement, battery drain/health, AirPods sound issues, hardware defect estimates.",
        "keywords": ["battery", "screen", "crack", "shatter", "shattered", "repair", "hardware", "airpods", "static", "water damage", "replacement"],
        "default_action": "AUTO_HANDLE",
        "escalation_reason": "General repair estimates and official service program notices can be auto-handled with KB link.",
        "knowledge_link": "https://support.apple.com/iphone/repair"
    },
    "SOFTWARE_UPDATE_BUG": {
        "description": "iOS/macOS update glitches, app crashing, system freezing, storage calculation errors, or feature bugs.",
        "keywords": ["update", "ios", "macos", "bug", "crash", "freeze", "pausing", "restart", "glitch", "slow"],
        "default_action": "AUTO_HANDLE",
        "escalation_reason": "Standard software troubleshooting steps and restart recommendations can be auto-handled.",
        "knowledge_link": "https://support.apple.com/HT201412"
    },
    "DEVICE_TRADEIN_SHIPPING": {
        "description": "Order tracking, delayed device shipment, trade-in kit status, or store delivery inquiries.",
        "keywords": ["order", "trade-in", "trade in", "shipping", "delivery", "kit", "track", "tracking", "status", "shipment"],
        "default_action": "ESCALATE",
        "escalation_reason": "Tracking specific order numbers requires private Direct Message (DM) to protect PII.",
        "knowledge_link": "https://www.apple.com/shop/trade-in"
    },
    "OTHER_GENERAL": {
        "description": "General how-to setup questions, device feature queries, data transfer from Android, store locations.",
        "keywords": ["how to", "transfer", "move to ios", "android", "store", "setup", "feature", "question", "info"],
        "default_action": "AUTO_HANDLE",
        "escalation_reason": "Standard self-serve setup and general knowledge links.",
        "knowledge_link": "https://support.apple.com"
    }
}

ESCALATION_KEYWORDS = [
    "dm", "direct message", "order #", "order number", "serial number",
    "stolen", "unauthorized", "legal", "lawyer", "refund", "sue", "police"
]

def check_mandatory_escalation(text: str) -> tuple[bool, str]:
    """Check if tweet contains strict privacy/safety triggers requiring escalation."""
    text_lower = text.lower()
    for kw in ["order #", "order number", "serial #", "serial number", "credit card", "ssn"]:
        if kw in text_lower:
            return True, "Contains sensitive PII (Order/Serial/Financial info) requiring private DM handling."
    for kw in ["hacked", "stolen", "unauthorized charge", "compromised"]:
        if kw in text_lower:
            return True, "Security compromise or unauthorized transaction detected."
    return False, ""
