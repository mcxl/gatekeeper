#!/usr/bin/env python3
"""
core/jurisdictions.py — Multi-jurisdiction support for SWMS generation.

Supports AU (Australia), NZ (New Zealand), UK (United Kingdom), US (United States).
Each jurisdiction defines legislation references, currency, date format, and
regulatory body information used across inference, rendering, and agent prompts.
"""

from __future__ import annotations

JURISDICTIONS: dict[str, dict] = {
    "AU": {
        "name": "Australia",
        "flag": "\U0001f1e6\U0001f1fa",
        "legislation": {
            "primary_act": "WHS Act 2011 (NSW)",
            "regulations": "WHS Regulation 2017 (NSW)",
            "codes_of_practice": "SafeWork NSW Codes of Practice",
        },
        "base_legislation_string": (
            "WHS Act 2011 (NSW) — WHS Regulation 2017 (NSW) — "
            "SafeWork NSW Codes of Practice"
        ),
        "regulator": "Safe Work Australia",
        "currency": "AUD",
        "date_format": "%d/%m/%Y",
        "phone_format": "+61",
        "site_address_example": "218 Vincent Rd Cranebrook NSW 2749",
        "pc_example": "mCXI",
        "induction_card": "White Card (CPCCWHS1001)",
    },
    "NZ": {
        "name": "New Zealand",
        "flag": "\U0001f1f3\U0001f1ff",
        "legislation": {
            "primary_act": "Health and Safety at Work Act 2015 (HSWA)",
            "regulations": "Health and Safety at Work (General Risk and Workplace Management) Regulations 2016",
            "codes_of_practice": "WorkSafe New Zealand Approved Codes of Practice",
        },
        "base_legislation_string": (
            "Health and Safety at Work Act 2015 (HSWA) — "
            "HSW General Risk and Workplace Management Regulations 2016 — "
            "WorkSafe New Zealand Approved Codes of Practice"
        ),
        "regulator": "WorkSafe New Zealand",
        "currency": "NZD",
        "date_format": "%d/%m/%Y",
        "phone_format": "+64",
        "site_address_example": "42 Quay Street, Auckland CBD 1010",
        "pc_example": "Fletcher Building",
        "induction_card": "Site Safe Passport",
    },
    "UK": {
        "name": "United Kingdom",
        "flag": "\U0001f1ec\U0001f1e7",
        "legislation": {
            "primary_act": "Health and Safety at Work etc. Act 1974",
            "regulations": "Management of Health and Safety at Work Regulations 1999",
            "cdm": "Construction (Design and Management) Regulations 2015 (CDM 2015)",
            "codes_of_practice": "HSE Approved Codes of Practice (ACOPs)",
        },
        "base_legislation_string": (
            "Health and Safety at Work etc. Act 1974 — "
            "CDM Regulations 2015 — "
            "Management of Health and Safety at Work Regulations 1999 — "
            "HSE Approved Codes of Practice"
        ),
        "regulator": "Health and Safety Executive (HSE)",
        "currency": "GBP",
        "date_format": "%d/%m/%Y",
        "phone_format": "+44",
        "site_address_example": "14 King's Cross Road, London WC1X 9HX",
        "pc_example": "Balfour Beatty",
        "induction_card": "CSCS Card",
    },
    "US": {
        "name": "United States",
        "flag": "\U0001f1fa\U0001f1f8",
        "legislation": {
            "primary_act": "Occupational Safety and Health Act of 1970",
            "regulations": "29 CFR 1926 (Construction Industry Standards)",
            "general_industry": "29 CFR 1910 (General Industry Standards)",
        },
        "base_legislation_string": (
            "OSHA Act of 1970 — "
            "29 CFR 1926 Construction Industry Standards — "
            "29 CFR 1910 General Industry Standards"
        ),
        "regulator": "Occupational Safety and Health Administration (OSHA)",
        "currency": "USD",
        "date_format": "%m/%d/%Y",
        "phone_format": "+1",
        "site_address_example": "350 Fifth Avenue, New York, NY 10118",
        "pc_example": "Turner Construction",
        "induction_card": "OSHA 10-Hour / 30-Hour Card",
    },
    "CA": {
        "name": "Canada",
        "flag": "\U0001f1e8\U0001f1e6",
        "legislation": {
            "primary_act": "Canada Labour Code Part II",
            "regulations": "Canada Occupational Health and Safety Regulations (SOR/86-304)",
            "whmis": "WHMIS 2015 (Hazardous Products Regulations)",
        },
        "base_legislation_string": (
            "Canada Labour Code Part II — "
            "Canada Occupational Health and Safety Regulations — "
            "WHMIS 2015"
        ),
        "regulator": "Canadian Centre for Occupational Health and Safety (CCOHS)",
        "currency": "CAD",
        "date_format": "%Y-%m-%d",
        "phone_format": "+1",
        "site_address_example": "100 Queen Street West, Toronto, ON M5H 2N2",
        "pc_example": "EllisDon",
        "induction_card": "Provincial OHS Awareness Training",
        "provinces": {
            "ON": {
                "name": "Ontario",
                "act": "Occupational Health and Safety Act (OHSA) R.S.O. 1990",
                "regulations": "O. Reg. 213/91 Construction Projects",
                "regulator": "Ontario Ministry of Labour, Immigration, Training and Skills Development",
            },
            "BC": {
                "name": "British Columbia",
                "act": "Workers Compensation Act (RSBC 2019)",
                "regulations": "OHS Regulation (BC Reg 296/97)",
                "regulator": "WorkSafeBC",
            },
            "AB": {
                "name": "Alberta",
                "act": "Occupational Health and Safety Act (SA 2020)",
                "regulations": "OHS Code 2009",
                "regulator": "Alberta OHS",
            },
            "QC": {
                "name": "Quebec",
                "act": "Act Respecting Occupational Health and Safety (CQLR c S-2.1)",
                "regulations": "Safety Code for the Construction Industry (CQLR c S-2.1, r.4)",
                "regulator": "CNESST",
            },
        },
    },
}

# ── Province-aware legislation for CA ────────────────────────────────────────

CA_PROVINCE_LEGISLATION: dict[str, str] = {
    "ON": (
        "Occupational Health and Safety Act R.S.O. 1990 — "
        "O. Reg. 213/91 Construction Projects — "
        "WHMIS 2015"
    ),
    "BC": (
        "Workers Compensation Act RSBC 2019 — "
        "OHS Regulation BC Reg 296/97 — "
        "WHMIS 2015"
    ),
    "AB": (
        "OHS Act SA 2020 — "
        "OHS Code 2009 — "
        "WHMIS 2015"
    ),
    "QC": (
        "Act Respecting OHS CQLR c S-2.1 — "
        "Safety Code for Construction Industry — "
        "WHMIS 2015"
    ),
}


def get_jurisdiction(code: str = "AU", ca_province: str = "") -> dict:
    """Return jurisdiction config dict. Defaults to AU if code not found.

    For CA, if ca_province is provided, overrides base_legislation_string
    with province-specific legislation.
    """
    jur = JURISDICTIONS.get(code.upper(), JURISDICTIONS["AU"]).copy()
    if code.upper() == "CA" and ca_province:
        prov = ca_province.upper()
        if prov in CA_PROVINCE_LEGISLATION:
            jur["base_legislation_string"] = CA_PROVINCE_LEGISLATION[prov]
        prov_data = jur.get("provinces", {}).get(prov)
        if prov_data:
            jur["regulator"] = prov_data["regulator"]
            jur["ca_province"] = prov
            jur["ca_province_name"] = prov_data["name"]
    return jur
