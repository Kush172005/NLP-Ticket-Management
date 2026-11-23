# Banking77 intent-to-department mapping

This table is generated from `ticket_routing.py`. The source labels are the exact 77 strings in `data/raw/categories.json`; the routing module checks for missing, unknown, or duplicate labels at startup. Departments are classroom prototype rules, not bank-approved policy.

| Exact intent label | Primary department |
|---|---|
| `card_payment_wrong_exchange_rate` | Card Payments Team |
| `card_payment_fee_charged` | Card Payments Team |
| `declined_card_payment` | Card Payments Team |
| `pending_card_payment` | Card Payments Team |
| `card_acceptance` | Card Payments Team |
| `contactless_not_working` | Card Payments Team |
| `apple_pay_or_google_pay` | Card Payments Team |
| `visa_or_mastercard` | Card Payments Team |
| `pending_cash_withdrawal` | Cash & ATM Team |
| `wrong_amount_of_cash_received` | Cash & ATM Team |
| `atm_support` | Cash & ATM Team |
| `declined_cash_withdrawal` | Cash & ATM Team |
| `wrong_exchange_rate_for_cash_withdrawal` | Cash & ATM Team |
| `cash_withdrawal_charge` | Cash & ATM Team |
| `balance_not_updated_after_cheque_or_cash_deposit` | Cash Deposit & Cheque Team |
| `top_up_by_cash_or_cheque` | Cash Deposit & Cheque Team |
| `extra_charge_on_statement` | Refund & Payments Team |
| `request_refund` | Refund & Payments Team |
| `Refund_not_showing_up` | Refund & Payments Team |
| `transaction_charged_twice` | Refund & Payments Team |
| `reverted_card_payment?` | Refund & Payments Team |
| `cancel_transfer` | Bank Transfer Team |
| `transfer_not_received_by_recipient` | Bank Transfer Team |
| `declined_transfer` | Bank Transfer Team |
| `pending_transfer` | Bank Transfer Team |
| `beneficiary_not_allowed` | Bank Transfer Team |
| `transfer_fee_charged` | Bank Transfer Team |
| `receiving_money` | Bank Transfer Team |
| `failed_transfer` | Bank Transfer Team |
| `transfer_into_account` | Bank Transfer Team |
| `transfer_timing` | Bank Transfer Team |
| `balance_not_updated_after_bank_transfer` | Bank Transfer Team |
| `card_arrival` | Card Services Team |
| `card_linking` | Card Services Team |
| `card_delivery_estimate` | Card Services Team |
| `card_not_working` | Card Services Team |
| `get_physical_card` | Card Services Team |
| `getting_virtual_card` | Card Services Team |
| `getting_spare_card` | Card Services Team |
| `card_swallowed` | Card Services Team |
| `disposable_card_limits` | Card Services Team |
| `order_physical_card` | Card Services Team |
| `virtual_card_not_working` | Card Services Team |
| `get_disposable_virtual_card` | Card Services Team |
| `activate_my_card` | Card Services Team |
| `card_about_to_expire` | Card Services Team |
| `supported_cards_and_currencies` | Card Services Team |
| `change_pin` | Card Services Team |
| `pin_blocked` | Card Services Team |
| `age_limit` | Account & Profile Team |
| `edit_personal_details` | Account & Profile Team |
| `why_verify_identity` | Account & Profile Team |
| `unable_to_verify_identity` | Account & Profile Team |
| `passcode_forgotten` | Account & Profile Team |
| `terminate_account` | Account & Profile Team |
| `verify_my_identity` | Account & Profile Team |
| `lost_or_stolen_card` | Fraud & Security Team |
| `card_payment_not_recognised` | Fraud & Security Team |
| `compromised_card` | Fraud & Security Team |
| `direct_debit_payment_not_recognised` | Fraud & Security Team |
| `lost_or_stolen_phone` | Fraud & Security Team |
| `verify_source_of_funds` | Fraud & Security Team |
| `cash_withdrawal_not_recognised` | Fraud & Security Team |
| `automatic_top_up` | Top-up & Funding Team |
| `top_up_by_bank_transfer_charge` | Top-up & Funding Team |
| `pending_top_up` | Top-up & Funding Team |
| `top_up_limits` | Top-up & Funding Team |
| `top_up_reverted` | Top-up & Funding Team |
| `topping_up_by_card` | Top-up & Funding Team |
| `verify_top_up` | Top-up & Funding Team |
| `top_up_failed` | Top-up & Funding Team |
| `top_up_by_card_charge` | Top-up & Funding Team |
| `exchange_rate` | International Payments Team |
| `fiat_currency_support` | International Payments Team |
| `exchange_via_app` | International Payments Team |
| `exchange_charge` | International Payments Team |
| `country_support` | International Payments Team |
