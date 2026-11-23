"""Central Banking77 intent routing and demo-agent configuration.

These department assignments are prototype rules chosen from each label's meaning;
Banking77 itself does not include departments or agent labels.
"""
from collections import Counter

from config import RAW
import json


DEPARTMENT_INTENTS = {
    "Card Payments Team": [
        "card_payment_wrong_exchange_rate", "card_payment_fee_charged",
        "declined_card_payment", "pending_card_payment", "card_acceptance",
        "contactless_not_working", "apple_pay_or_google_pay", "visa_or_mastercard",
    ],
    "Cash & ATM Team": [
        "pending_cash_withdrawal", "wrong_amount_of_cash_received",
        "atm_support", "declined_cash_withdrawal", "wrong_exchange_rate_for_cash_withdrawal",
        "cash_withdrawal_charge",
    ],
    "Cash Deposit & Cheque Team": [
        "balance_not_updated_after_cheque_or_cash_deposit", "top_up_by_cash_or_cheque",
    ],
    "Refund & Payments Team": [
        "extra_charge_on_statement", "request_refund", "Refund_not_showing_up",
        "transaction_charged_twice", "reverted_card_payment?",
    ],
    "Bank Transfer Team": [
        "cancel_transfer", "transfer_not_received_by_recipient", "declined_transfer",
        "pending_transfer", "beneficiary_not_allowed", "transfer_fee_charged",
        "receiving_money", "failed_transfer", "transfer_into_account", "transfer_timing",
        "balance_not_updated_after_bank_transfer",
    ],
    "Card Services Team": [
        "card_arrival", "card_linking", "card_delivery_estimate", "card_not_working",
        "get_physical_card", "getting_virtual_card", "getting_spare_card", "card_swallowed",
        "disposable_card_limits", "order_physical_card", "virtual_card_not_working",
        "get_disposable_virtual_card", "activate_my_card", "card_about_to_expire",
        "supported_cards_and_currencies", "change_pin", "pin_blocked",
    ],
    "Account & Profile Team": [
        "age_limit", "edit_personal_details", "why_verify_identity",
        "unable_to_verify_identity", "passcode_forgotten", "terminate_account",
        "verify_my_identity",
    ],
    "Fraud & Security Team": [
        "lost_or_stolen_card", "card_payment_not_recognised", "compromised_card",
        "direct_debit_payment_not_recognised", "lost_or_stolen_phone",
        "verify_source_of_funds", "cash_withdrawal_not_recognised",
    ],
    "Top-up & Funding Team": [
        "automatic_top_up", "top_up_by_bank_transfer_charge", "pending_top_up",
        "top_up_limits", "top_up_reverted", "topping_up_by_card", "verify_top_up",
        "top_up_failed", "top_up_by_card_charge",
    ],
    "International Payments Team": [
        "exchange_rate", "fiat_currency_support", "exchange_via_app", "exchange_charge",
        "country_support",
    ],
}

INTENT_TO_DEPARTMENT = {
    intent: department
    for department, intents in DEPARTMENT_INTENTS.items()
    for intent in intents
}
INTENT_TO_QUEUE = INTENT_TO_DEPARTMENT  # Existing API/UI name retained for compatibility.

DATASET_INTENTS = json.loads((RAW / "categories.json").read_text(encoding="utf-8"))
_counts = Counter(intent for intents in DEPARTMENT_INTENTS.values() for intent in intents)
_missing = sorted(set(DATASET_INTENTS) - set(INTENT_TO_DEPARTMENT))
_unknown = sorted(set(INTENT_TO_DEPARTMENT) - set(DATASET_INTENTS))
_duplicates = sorted(intent for intent, count in _counts.items() if count != 1)
if _missing or _unknown or _duplicates:
    raise RuntimeError(
        f"Department mapping must cover each dataset label exactly once: "
        f"missing={_missing}, unknown={_unknown}, duplicates={_duplicates}"
    )

DEMO_AGENTS = {
    "Card Payments Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Cash & ATM Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Cash Deposit & Cheque Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Refund & Payments Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Bank Transfer Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Card Services Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Account & Profile Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Fraud & Security Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "Top-up & Funding Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
    "International Payments Team": ["Rahul Sharma", "Priya Mehta", "Arjun Verma", "Neha Kapoor"],
}


def department_for_intent(intent):
    """Look up the one configured department; unknown labels fail explicitly."""
    try:
        return INTENT_TO_DEPARTMENT[intent]
    except KeyError as error:
        raise ValueError("intent_not_in_department_mapping") from error


def queue_for_intent(intent):
    """Backwards-compatible alias used by saved review decisions."""
    return department_for_intent(intent)


def get_departments():
    return [
        {"name": department, "intent_count": len(intents), "intents": intents}
        for department, intents in DEPARTMENT_INTENTS.items()
    ]


def get_demo_agents(department=None):
    if department is not None:
        return DEMO_AGENTS.get(department, [])
    return DEMO_AGENTS
