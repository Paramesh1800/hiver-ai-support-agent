# Annotation & Labelling Guide — @AppleSupport Golden Evaluation Set

This document defines the ground-truth annotation rules for human labelling of the 200-sample Golden Evaluation Set (`data/golden/golden_set_unlabelled.csv` -> `data/golden/golden_set_labelled.json`).

---

## 1. Intent Taxonomy Definitions (6 Categories)

### 1. `ACCOUNT_SECURITY`
- **Definition**: Apple ID lockouts, 2FA verification codes, password resets, unauthorized logins, or compromised security.
- **Positive Example**: *"I am locked out of my Apple ID and cannot receive 2FA text code."*
- **Negative Example**: *"My App Store billing payment failed."* (→ `BILLING_SUBSCRIPTIONS`)

### 2. `BILLING_SUBSCRIPTIONS`
- **Definition**: Unrecognized credit card charges, App Store refund requests, subscription cancellations, or payment method declines.
- **Positive Example**: *"I see an unauthorized charge of $14.99 from ITUNES.COM on my card."*
- **Negative Example**: *"My phone battery is draining fast."* (→ `HARDWARE_REPAIR`)

### 3. `HARDWARE_REPAIR`
- **Definition**: Physical device damage, shattered screen, battery drain/degradation, AirPods static, or hardware repair estimates.
- **Positive Example**: *"My iPhone 14 battery drops from 100% to 20% in 2 hours."*
- **Negative Example**: *"iOS update failed to install."* (→ `SOFTWARE_UPDATE_BUG`)

### 4. `SOFTWARE_UPDATE_BUG`
- **Definition**: iOS/macOS update glitches, app crashing, system freezing, storage calculation errors, or audio playback bugs.
- **Positive Example**: *"Apple Music keeps pausing after 5 seconds on iOS 17.2."*
- **Negative Example**: *"My trade-in box hasn't arrived."* (→ `DEVICE_TRADEIN_SHIPPING`)

### 5. `DEVICE_TRADEIN_SHIPPING`
- **Definition**: Order tracking, delayed shipment of new devices, trade-in kit delivery, or store delivery inquiries.
- **Positive Example**: *"My trade-in kit hasn't arrived and it has been 10 days since order W98234."*
- **Negative Example**: *"How do I back up my iPhone?"* (→ `OTHER_GENERAL`)

### 6. `OTHER_GENERAL`
- **Definition**: General how-to questions, feature setup, Android-to-iOS data transfer, store hours, or general inquiries.
- **Positive Example**: *"How do I transfer WhatsApp chats from Android to my new iPhone?"*
- **Negative Example**: *"Password reset link is broken."* (→ `ACCOUNT_SECURITY`)

---

## 2. Action Rules: `ESCALATE` vs `AUTO_HANDLE`

- **Mark `ESCALATE` if ANY of the following apply**:
  1. The issue involves account security, Apple ID lockouts, or 2FA credentials (requires secure web portal authentication).
  2. The query involves monetary charges, refund requests, or payment card disputes (requires private billing portal).
  3. The message contains private PII (Order number, Serial number, Credit Card info) requiring private Direct Message (DM).
  4. The user expresses severe hostility, legal threats, or explicitly asks for a human manager.

- **Mark `AUTO_HANDLE` if ALL of the following apply**:
  1. The issue can be resolved with standard self-serve troubleshooting or official Apple Knowledge Base (KB) support URLs.
  2. The query asks for public information (store hours, repair price estimates, update instructions, Move to iOS app).
  3. No private PII or authentication is required to answer.

---

## 3. Tie-Breaking Rules for Ambiguous Cases

1. **Multi-Intent Messages**: If a tweet contains multiple issues (e.g., *"My battery drains AND I was charged $9.99"*), select the intent that requires **`ESCALATE`** (`BILLING_SUBSCRIPTIONS` over `HARDWARE_REPAIR`). Safety/billing takes priority over technical troubleshooting.
2. **Pure Rants with No Clear Request** (e.g., *"@AppleSupport iOS 17 is the worst software ever written!!!"*):
   - Label intent as `SOFTWARE_UPDATE_BUG`.
   - Label action as `AUTO_HANDLE` (provide standard update feedback link).
3. **Short / Ambiguous Help Messages** (e.g., *"@AppleSupport help"* or *"DM me"*):
   - Label intent as `OTHER_GENERAL`.
   - Label action as `AUTO_HANDLE` (ask user for details).