#!/usr/bin/env python3
"""
Seed HCPCS code data for quick lookup (stored in process_docs.py).

This script just validates and prints the code database.
"""

CGM_CODES = {
    "A9276": {
        "short": "CGM sensor",
        "long": "Sensor; invasive (e.g., subcutaneous), disposable, for use with interstitial continuous glucose monitoring system, one unit",
        "category": "cgm_supplies",
        "pricing": "consumable",
        "modifiers": ["KX", "NU"],
        "bundling": ["Must match transmitter/receiver system"],
        "lcd": "L33822",
        "notes": "Typically replaced every 10-14 days. Dexcom G6/G7, Freestyle Libre 2/3.",
    },
    "A9277": {
        "short": "CGM transmitter",
        "long": "Transmitter; external, for use with interstitial continuous glucose monitoring system",
        "category": "cgm_supplies",
        "pricing": "consumable",
        "modifiers": ["KX", "NU"],
        "bundling": ["Must match sensor system"],
        "lcd": "L33822",
        "notes": "Replacement frequency: Dexcom 90 days, Libre integrated with sensor.",
    },
    "A9278": {
        "short": "CGM receiver",
        "long": "Receiver (monitor); external, for use with interstitial continuous glucose monitoring system",
        "category": "cgm_equipment",
        "pricing": "purchase_or_rental",
        "modifiers": ["KX", "NU", "RR"],
        "bundling": ["One per beneficiary unless replacement needed"],
        "lcd": "L33822",
        "notes": "Many patients use smartphone app instead. NU for new, RR for rental.",
    },
    "K0553": {
        "short": "CGM monthly supply",
        "long": "Supply allowance for therapeutic continuous glucose monitor (CGM), includes all supplies and accessories, 1 month supply",
        "category": "cgm_monthly",
        "pricing": "monthly_supply",
        "modifiers": ["KX"],
        "bundling": ["Cannot bill with A9276/A9277/A9278 - all inclusive"],
        "lcd": "L33822",
        "notes": "Newer all-inclusive code. Covers all CGM supplies for one month.",
    },
    "K0554": {
        "short": "CGM receiver (K0553)",
        "long": "Receiver (monitor); dedicated, for use with therapeutic glucose continuous monitor system",
        "category": "cgm_equipment",
        "pricing": "purchase",
        "modifiers": ["KX", "NU"],
        "bundling": ["Use with K0553 system only"],
        "lcd": "L33822",
        "notes": "Receiver for K0553 monthly supply patients.",
    },
    "E2102": {
        "short": "Adjunctive CGM receiver",
        "long": "Adjunctive continuous glucose monitor or receiver",
        "category": "cgm_adjunctive",
        "pricing": "purchase_or_rental",
        "modifiers": ["NU", "RR"],
        "bundling": [],
        "lcd": None,
        "notes": "For non-therapeutic/adjunctive use. Does not require medical necessity.",
    },
    "E2103": {
        "short": "Non-adjunctive CGM receiver",
        "long": "Non-adjunctive continuous glucose monitor or receiver",
        "category": "cgm_equipment",
        "pricing": "purchase_or_rental",
        "modifiers": ["KX", "NU", "RR"],
        "bundling": [],
        "lcd": "L33822",
        "notes": "Therapeutic CGM receiver. Requires medical necessity documentation.",
    },
}

MODIFIERS = {
    "KX": {
        "description": "Requirements specified in the medical policy have been met",
        "usage": "Required for CGM claims to indicate LCD L33822 criteria are met and documented",
    },
    "NU": {
        "description": "New equipment",
        "usage": "For purchase of new DME equipment",
    },
    "RR": {
        "description": "Rental",
        "usage": "For monthly rental of DME equipment",
    },
    "GA": {
        "description": "Waiver of liability statement on file",
        "usage": "ABN signed for potentially non-covered service",
    },
    "GY": {
        "description": "Item or service statutorily excluded",
        "usage": "Service is never covered by Medicare",
    },
    "GZ": {
        "description": "Item or service expected to be denied as not reasonable/necessary",
        "usage": "No ABN on file, non-covered service",
    },
}


def main():
    """Print code database for verification."""
    print("CGM HCPCS Code Database")
    print("=" * 60)

    for code, info in CGM_CODES.items():
        print(f"\n{code}: {info['short']}")
        print(f"  Category: {info['category']}")
        print(f"  Pricing: {info['pricing']}")
        print(f"  Modifiers: {', '.join(info['modifiers'])}")
        print(f"  LCD: {info['lcd'] or 'N/A'}")

    print("\n" + "=" * 60)
    print("Common Modifiers")
    print("=" * 60)

    for mod, info in MODIFIERS.items():
        print(f"\n{mod}: {info['description']}")
        print(f"  Usage: {info['usage']}")


if __name__ == "__main__":
    main()
