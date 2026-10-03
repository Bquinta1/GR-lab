from typing import Any


FAKE_CLAIM: dict[str, dict[str, Any]] = {
    "WC-2026-0042": {
        "claim_id": "WC-2026-0042",
        "customer_name": "Maya Example",
        "email": "maya@example.test",
        "phone": "555-0102",
        "address": "123 Example Lane, Rockville, MD",
        "product": "AcmeCool Refrigerator",
        "serial_number": "ACR-FAKE-8821",
        "status": "inspection scheduled",
        "notes": (
            "Customer requested a refund. "
            "Payment reference: card 4111 1111 1111 1111"
        ),
    }
}


def get_claim(claim_id: str) -> dict[str, Any]:
    if claim_id not in FAKE_CLAIM:
        raise ValueError(f"Unknown claim: {claim_id}")

    return FAKE_CLAIM[claim_id].copy()


def send_to_repair_partner(claim_id: str) -> dict[str, Any]:
    from control import for_partner

    claim = get_claim(claim_id)
    payload = for_partner(claim)
    print("OUTBOUND PARTNER PAYLOAD:")
    print(payload)

    return {
        "status": "accepted",
        "partner_reference": "RP-2026-0091",
        "payload_sent": payload,
    }
