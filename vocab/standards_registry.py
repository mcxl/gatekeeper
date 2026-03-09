#!/usr/bin/env python3
"""
vocab/standards_registry.py — Verified standards registry and citation validator.

Only standards that actually exist and are current are included.
Used to prevent hallucinated standard numbers in generated documents.
"""

import re

# ── Verified Standards Registry ──────────────────────────────────────────────

VERIFIED_STANDARDS = {
    "AU": {
        "working_at_heights": [
            "AS/NZS 1891.1 — Industrial fall-arrest systems and devices — Harnesses and ancillary equipment",
            "AS/NZS 1891.4 — Industrial fall-arrest systems — Selection, use and maintenance",
            "AS/NZS 1892.1 — Portable ladders — Metal",
            "AS/NZS 1892.3 — Portable ladders — Reinforced plastic",
            "AS/NZS 4994.1 — Temporary edge protection",
            "Safe Work Australia Code of Practice — Managing the Risk of Falls at Workplaces",
        ],
        "scaffolding": [
            "AS/NZS 4576 — Guidelines for scaffolding safety",
            "AS 1576.1 — Scaffolding — General requirements",
            "AS 1576.2 — Scaffolding — Couplers and accessories",
            "AS 1576.3 — Scaffolding — Prefabricated and tube-and-coupler scaffolding",
            "Safe Work Australia Code of Practice — Construction Work",
        ],
        "electrical": [
            "AS/NZS 3000 — Wiring rules",
            "AS/NZS 3012 — Electrical installations — Construction and demolition sites",
            "AS/NZS 4836 — Safe working on or near low-voltage electrical installations",
            "Safe Work Australia Code of Practice — Managing Electrical Risks in the Workplace",
        ],
        "cranes_lifting": [
            "AS 2550.1 — Cranes, hoists and winches — General requirements",
            "AS 2550.5 — Mobile and vehicle-loading cranes",
            "AS 1418.1 — Cranes, hoists and winches — General requirements",
            "AS 2550.10 — Elevating work platforms",
            "Safe Work Australia Code of Practice — Cranes",
        ],
        "silica_dust": [
            "Safe Work Australia Code of Practice — Manufactured Stone",
            "Safe Work Australia Guidance — Respirable Crystalline Silica from Stone in the Construction Industry",
            "AS 1716 — Respiratory protective devices",
            "AS/NZS 1715 — Selection, use and maintenance of respiratory protective equipment",
        ],
        "asbestos": [
            "Safe Work Australia Code of Practice — How to Manage and Control Asbestos in the Workplace",
            "Safe Work Australia Code of Practice — How to Safely Remove Asbestos",
            "AS/NZS 4801 — Occupational health and safety management systems",
        ],
        "confined_space": [
            "Safe Work Australia Code of Practice — Confined Spaces",
            "AS 2865 — Confined spaces",
        ],
        "excavation": [
            "Safe Work Australia Code of Practice — Excavation Work",
        ],
        "hazardous_chemicals": [
            "Safe Work Australia Code of Practice — Managing Risks of Hazardous Chemicals in the Workplace",
            "Safe Work Australia Code of Practice — Labelling of Workplace Hazardous Chemicals",
            "Safe Work Australia Code of Practice — Preparation of Safety Data Sheets for Hazardous Chemicals",
            "AS 3780 — The storage and handling of corrosive substances",
        ],
        "manual_handling": [
            "Safe Work Australia Code of Practice — Hazardous Manual Tasks",
        ],
        "noise": [
            "Safe Work Australia Code of Practice — Managing Noise and Preventing Hearing Loss at Work",
            "AS/NZS 1269.3 — Occupational noise management — Hearing protector program",
        ],
        "ppe": [
            "AS/NZS 1337.1 — Personal eye protection — Eye and face protectors for occupational applications",
            "AS/NZS 1716 — Respiratory protective devices",
            "AS/NZS 2161.1 — Occupational protective gloves — Selection, use and maintenance",
            "AS/NZS 1800 — Occupational protective helmets",
            "AS/NZS 2210.1 — Safety, protective and occupational footwear",
        ],
        "traffic_management": [
            "AS 1742.3 — Manual of uniform traffic control devices — Traffic control devices for works on roads",
            "Safe Work Australia Code of Practice — Traffic Management at Worksites",
        ],
        "tilt_up": [
            "Safe Work Australia Code of Practice — Tilt-up and Precast Concrete",
            "AS 3850.1 — Prefabricated concrete elements — Tolerances and testing of elements",
        ],
        "demolition": [
            "Safe Work Australia Code of Practice — Demolition Work",
            "AS 2601 — Demolition of structures",
        ],
        "formwork": [
            "Safe Work Australia Code of Practice — Formwork",
            "AS 3610 — Formwork for concrete",
        ],
        "general_construction": [
            "Safe Work Australia Code of Practice — Construction Work",
            "Safe Work Australia Code of Practice — Work Health and Safety Consultation, Cooperation and Coordination",
            "Safe Work Australia Code of Practice — First Aid in the Workplace",
            "Safe Work Australia Code of Practice — Managing the Work Environment and Facilities",
        ],
    },

    "NZ": {
        "working_at_heights": [
            "WorkSafe NZ Good Practice Guide — Working at Height",
            "AS/NZS 1891.1 — Industrial fall-arrest systems and devices",
            "AS/NZS 1892.1 — Portable ladders — Metal",
            "NZS 3604 — Timber-framed buildings (structural reference)",
        ],
        "scaffolding": [
            "WorkSafe NZ Good Practice Guide — Scaffolding",
            "AS/NZS 4576 — Guidelines for scaffolding safety",
        ],
        "electrical": [
            "Electricity Act 1992 (NZ)",
            "Electricity (Safety) Regulations 2010 (NZ)",
            "AS/NZS 3000 — Wiring rules",
        ],
        "cranes_lifting": [
            "WorkSafe NZ Approved Code of Practice — Cranes",
            "AS 2550.1 — Cranes, hoists and winches",
        ],
        "asbestos": [
            "Health and Safety at Work (Asbestos) Regulations 2016 (NZ)",
            "WorkSafe NZ Approved Code of Practice — Management and Removal of Asbestos",
        ],
        "confined_space": [
            "WorkSafe NZ Approved Code of Practice — Safe Work in Confined Spaces",
            "AS 2865 — Confined spaces",
        ],
        "excavation": [
            "WorkSafe NZ Approved Code of Practice — Excavations",
        ],
        "hazardous_chemicals": [
            "Health and Safety at Work (Hazardous Substances) Regulations 2017 (NZ)",
            "WorkSafe NZ Guidance — Hazardous Substances",
        ],
        "general_construction": [
            "Health and Safety at Work Act 2015 (NZ)",
            "Health and Safety at Work (General Risk and Workplace Management) Regulations 2016 (NZ)",
            "WorkSafe NZ Good Practice Guide — Construction Health and Safety",
        ],
    },

    "UK": {
        "working_at_heights": [
            "Work at Height Regulations 2005",
            "HSE Approved Code of Practice — Work at Height",
            "BS EN 363 — Personal fall protection systems",
            "BS EN 361 — Full body harnesses",
            "BS EN 131 — Ladders",
        ],
        "scaffolding": [
            "BS EN 12811-1 — Temporary works equipment — Scaffolds — Performance requirements and general design",
            "NASC Technical Guidance TG20 — Scaffolding",
            "HSE Guidance — General Access Scaffolding and Ladders",
        ],
        "electrical": [
            "Electricity at Work Regulations 1989",
            "BS 7671 — Requirements for Electrical Installations (IET Wiring Regulations)",
            "HSE Guidance — Electrical Safety on Construction Sites",
        ],
        "cranes_lifting": [
            "Lifting Operations and Lifting Equipment Regulations 1998 (LOLER)",
            "Provision and Use of Work Equipment Regulations 1998 (PUWER)",
            "BS 7121 — Safe use of cranes",
            "HSE Guidance — Lifting Operations and Lifting Equipment",
        ],
        "asbestos": [
            "Control of Asbestos Regulations 2012",
            "HSE Approved Code of Practice — Managing and Working with Asbestos",
        ],
        "confined_space": [
            "Confined Spaces Regulations 1997",
            "HSE Approved Code of Practice — Safe Work in Confined Spaces",
        ],
        "excavation": [
            "HSE Guidance — Excavations — Health and Safety in Construction",
            "BS 6031 — Code of practice for earthworks",
        ],
        "hazardous_chemicals": [
            "Control of Substances Hazardous to Health Regulations 2002 (COSHH)",
            "HSE Approved Code of Practice — Control of Substances Hazardous to Health",
        ],
        "manual_handling": [
            "Manual Handling Operations Regulations 1992",
            "HSE Guidance — Getting to Grips with Manual Handling",
        ],
        "cdm": [
            "Construction (Design and Management) Regulations 2015 (CDM 2015)",
            "HSE Approved Code of Practice — Managing Health and Safety in Construction (CDM 2015)",
        ],
        "noise": [
            "Control of Noise at Work Regulations 2005",
            "BS EN 458 — Hearing protectors — Recommendations for selection, use, care and maintenance",
        ],
        "general_construction": [
            "Health and Safety at Work Act 1974",
            "Management of Health and Safety at Work Regulations 1999",
            "Construction (Design and Management) Regulations 2015",
            "Personal Protective Equipment at Work Regulations 1992",
        ],
    },

    "US": {
        "working_at_heights": [
            "29 CFR 1926.502 — Fall protection systems criteria and practices",
            "29 CFR 1926.503 — Training requirements for fall protection",
            "29 CFR 1926.501 — Duty to have fall protection",
            "ANSI/ASSP Z359.1 — Safety requirements for personal fall arrest systems",
        ],
        "scaffolding": [
            "29 CFR 1926.451 — General requirements for scaffolds",
            "29 CFR 1926.452 — Additional requirements applicable to specific types of scaffolds",
            "29 CFR 1926.454 — Training requirements for scaffolding",
            "ANSI/ASSP A10.8 — Scaffolding safety requirements",
        ],
        "electrical": [
            "29 CFR 1926.400 — General electrical requirements",
            "29 CFR 1926.416 — General requirements for electrical safety",
            "29 CFR 1926.417 — Lockout and tagging of circuits",
            "NFPA 70E — Standard for electrical safety in the workplace",
        ],
        "cranes_lifting": [
            "29 CFR 1926.1400 — Cranes and derricks in construction",
            "29 CFR 1926.1410 — Power line safety",
            "29 CFR 1926.251 — Rigging equipment for material handling",
            "ASME B30.5 — Mobile and locomotive cranes",
        ],
        "silica_dust": [
            "29 CFR 1926.1153 — Respirable crystalline silica",
            "OSHA Table 1 — Specified exposure control methods for silica",
            "NIOSH Publication — Controlling Silica Exposures in Construction",
        ],
        "asbestos": [
            "29 CFR 1926.1101 — Asbestos in construction",
            "40 CFR Part 61 — NESHAP for asbestos",
            "OSHA Guidance — Asbestos in Construction",
        ],
        "confined_space": [
            "29 CFR 1926.1201 — Confined spaces in construction — General",
            "29 CFR 1926.1203 — Permit-required confined spaces",
            "29 CFR 1926.1211 — Rescue and emergency services",
        ],
        "excavation": [
            "29 CFR 1926.651 — Specific excavation requirements",
            "29 CFR 1926.652 — Requirements for protective systems",
            "OSHA Guidance — Excavation and Trenching",
        ],
        "hazardous_chemicals": [
            "29 CFR 1926.59 — Hazard communication",
            "29 CFR 1910.1200 — Hazard communication standard (HazCom/GHS)",
            "OSHA Guidance — Hazard Communication",
        ],
        "manual_handling": [
            "OSHA Guidance — Ergonomics for Construction",
            "NIOSH Lifting Equation — Applications Manual",
        ],
        "noise": [
            "29 CFR 1926.52 — Occupational noise exposure",
            "29 CFR 1910.95 — Occupational noise exposure",
            "ANSI S3.19 — Method for the measurement of real-ear hearing protector attenuation",
        ],
        "ppe": [
            "29 CFR 1926.95 — Criteria for personal protective equipment",
            "29 CFR 1926.100 — Head protection",
            "29 CFR 1926.101 — Hearing protection",
            "29 CFR 1926.102 — Eye and face protection",
            "ANSI/ISEA Z87.1 — Occupational and educational personal eye and face protection devices",
            "ANSI/ISEA Z89.1 — Industrial head protection",
        ],
        "general_construction": [
            "29 CFR Part 1926 — Safety and health regulations for construction",
            "OSH Act 1970 — Occupational Safety and Health Act",
            "OSHA 29 CFR 1926.20 — General safety and health provisions",
        ],
    },

    "CA": {
        "working_at_heights": [
            "Canada OHS Regulation Part XII — Safety Nets",
            "Canada OHS Regulation s.12.10 — Fall protection",
            "CSA Z259.10 — Full body harnesses",
            "CSA Z259.11 — Energy absorbers and lanyards",
            "Ontario — O. Reg 213/91 s.26-30 — Fall protection",
            "WorkSafeBC OHS Regulation Part 11 — Fall protection",
            "Alberta OHS Code Part 9 — Fall protection",
        ],
        "scaffolding": [
            "CSA S269.2 — Access scaffolding for construction purposes",
            "Ontario — O. Reg 213/91 Part VIII — Scaffolds",
            "WorkSafeBC OHS Regulation Part 13 — Scaffolds and temporary work platforms",
        ],
        "electrical": [
            "Canadian Electrical Code Part 1 (CSA C22.1)",
            "Canada OHS Regulation Part XIV — Electrical safety",
            "Ontario Electrical Safety Code",
        ],
        "cranes_lifting": [
            "CSA B167 — Overhead cranes, gantry cranes, monorails, hoists and hooks",
            "CSA Z150 — Safety code on mobile cranes",
            "Ontario — O. Reg 213/91 Part VI — Cranes and hoisting equipment",
            "WorkSafeBC OHS Regulation Part 14 — Rigging",
        ],
        "asbestos": [
            "Canada Labour Code — Asbestos abatement requirements",
            "Ontario — O. Reg 278/05 — Designated Substance — Asbestos on Construction Projects",
            "WorkSafeBC OHS Regulation Part 6.1 — Asbestos",
            "Alberta OHS Code Part 4 — Chemical hazards — Asbestos",
        ],
        "confined_space": [
            "Canada OHS Regulation Part XI — Confined spaces",
            "CSA Z1006 — Management of work in confined spaces",
            "Ontario — O. Reg 632/05 — Confined spaces",
            "WorkSafeBC OHS Regulation Part 9 — Confined spaces",
        ],
        "hazardous_chemicals": [
            "WHMIS 2015 — Workplace Hazardous Materials Information System",
            "Canada Hazardous Products Act",
            "Canada Hazardous Products Regulations 2015",
            "CCOHS Guidance — WHMIS 2015",
        ],
        "silica_dust": [
            "CCOHS Guidance — Silica — Health Effects and Exposure Limits",
            "Ontario — Designated Substance — Silica Regulation",
            "WorkSafeBC OHS Regulation s.5.54 — Silica",
        ],
        "noise": [
            "Canada OHS Regulation Part VII — Levels of sound",
            "CSA Z94.2 — Hearing protection devices — Performance, selection, care and use",
            "Ontario — O. Reg 381/15 — Designated Substance — Noise",
        ],
        "general_construction": [
            "Canada Labour Code Part II — Occupational Health and Safety",
            "Canada OHS Regulations",
            "CCOHS Guidance — Construction Safety",
            "Ontario — Occupational Health and Safety Act 1990 (OHSA)",
            "Ontario — O. Reg 213/91 — Construction Projects",
            "WorkSafeBC — OHS Regulation",
            "Alberta OHS Act 2020",
        ],
    },
}


# ── CCVS code to category mapping ────────────────────────────────────────────

CCVS_TO_CATEGORY = {
    "WAH": "working_at_heights",
    "WFA": "working_at_heights",
    "WFR": "working_at_heights",
    "SCF": "scaffolding",
    "ELE": "electrical",
    "MOB": "cranes_lifting",
    "CRN": "cranes_lifting",
    "SIL": "silica_dust",
    "ASB": "asbestos",
    "CFS": "confined_space",
    "EXC": "excavation",
    "CHM": "hazardous_chemicals",
    "MNH": "manual_handling",
    "NOI": "noise",
    "TRF": "traffic_management",
    "TLT": "tilt_up",
    "DEM": "demolition",
    "FMW": "formwork",
    "STR": "general_construction",
    "IRA": "general_construction",
    "ENE": "general_construction",
    "HOT": "general_construction",
    "LED": "hazardous_chemicals",
    "ENV": "general_construction",
}


# ── Standard number detection pattern ────────────────────────────────────────

STANDARD_NUMBER_PATTERN = re.compile(
    r'\b(?:'
    r'AS/?NZS?\s*\d{3,5}'         # AS/NZS XXXX or AS XXXX
    r'|BS\s+(?:EN\s+)?\d{3,5}'    # BS/BS EN XXXX
    r'|CSA\s+[A-Z]\d{2,4}'        # CSA AXXXX
    r'|29\s+CFR\s+\d{4}\.\d+'     # 29 CFR XXXX.X
    r'|40\s+CFR\s+Part\s+\d+'     # 40 CFR Part XX
    r'|ANSI/\w+\s+\w+[\d.]+'      # ANSI/XXXX
    r'|NFPA\s+\d+'                 # NFPA XX
    r'|ISO\s+\d{3,5}'             # ISO XXXXX
    r'|NZS\s+\d{4}'               # NZS XXXX
    r'|ASME\s+B\d+\.\d+'          # ASME B30.5
    r')\b',
    re.IGNORECASE
)


# ── Functions ────────────────────────────────────────────────────────────────

def get_verified_standards(
    jurisdiction: str,
    ccvs_codes: list,
    include_general: bool = True,
) -> list[str]:
    """Return verified standards list for jurisdiction and detected hazard codes."""
    j = jurisdiction.upper()
    registry = VERIFIED_STANDARDS.get(j, VERIFIED_STANDARDS["AU"])

    standards: list[str] = []

    if include_general:
        standards.extend(registry.get("general_construction", []))

    for code in ccvs_codes:
        base_code = code.split("-")[0].upper()
        category = CCVS_TO_CATEGORY.get(base_code)
        if category:
            for s in registry.get(category, []):
                if s not in standards:
                    standards.append(s)

    return standards


def validate_standard_citations(
    text: str,
    jurisdiction: str,
    ccvs_codes: list,
) -> dict:
    """Scan text for standard number citations. Flag any not in the verified registry."""
    # Build flat list of all verified standards for this jurisdiction
    j = jurisdiction.upper()
    registry = VERIFIED_STANDARDS.get(j, VERIFIED_STANDARDS["AU"])
    all_standards: list[str] = []
    for category_standards in registry.values():
        all_standards.extend(category_standards)

    found_numbers = STANDARD_NUMBER_PATTERN.findall(text)

    verified: list[str] = []
    flagged: list[str] = []

    for number in found_numbers:
        number_clean = number.strip().upper()
        is_verified = any(number_clean in s.upper() for s in all_standards)
        if is_verified:
            verified.append(number)
        else:
            flagged.append(number)

    return {
        "verified": verified,
        "flagged": flagged,
        "flag_count": len(flagged),
    }


def strip_unverified_citations(
    text: str,
    jurisdiction: str,
    ccvs_codes: list,
) -> str:
    """Remove unverified standard number citations from text."""
    result = validate_standard_citations(text, jurisdiction, ccvs_codes)

    if not result["flagged"]:
        return text

    cleaned = text
    for flagged_number in result["flagged"]:
        cleaned = cleaned.replace(flagged_number, "")

    # Clean up artifacts
    cleaned = re.sub(r'  +', ' ', cleaned)
    cleaned = re.sub(r' \)', ')', cleaned)
    cleaned = re.sub(r'\( ', '(', cleaned)

    return cleaned.strip()


# ── Jurisdiction signal detection ────────────────────────────────────────────

JURISDICTION_SIGNALS = {
    "AU": [
        "nsw", "vic", "qld", "sa", "wa", "tas",
        "act", "nt", "safework", "pcbu", "hrcw",
        "swms", "workcover", "sydney", "melbourne",
        "brisbane", "perth", "adelaide", "darwin",
        "canberra", "hobart", "icare", "sira",
    ],
    "NZ": [
        "worksafe nz", "worksafe new zealand",
        "hswa", "acc", "auckland", "wellington",
        "christchurch", "hamilton", "tauranga",
        "dunedin", "notifiable work", "nzs",
    ],
    "UK": [
        "hse", "cdm", "method statement",
        "principal designer", "f10", "coshh",
        "loler", "puwer", "london", "manchester",
        "birmingham", "leeds", "glasgow",
        "edinburgh", "cardiff", "belfast", "bs en",
    ],
    "US": [
        "osha", "cfr", "competent person",
        "aha", "jha", "sssp", "new york",
        "los angeles", "chicago", "houston",
        "nfpa", "ansi", "niosh",
    ],
    "CA": [
        "wsib", "worksafebc", "ccohs", "ontario",
        "alberta", "british columbia", "quebec",
        "csa", "whmis", "toronto", "vancouver",
        "calgary", "edmonton", "montreal",
        "o. reg", "ohsa", "constructor",
    ],
}


def detect_jurisdiction_from_query(
    query: str,
    selected_jurisdiction: str,
) -> dict:
    """Check if query contains signals suggesting a different jurisdiction."""
    query_lower = query.lower()
    signal_counts: dict[str, int] = {}

    for jur, signals in JURISDICTION_SIGNALS.items():
        count = sum(1 for signal in signals if signal in query_lower)
        if count > 0:
            signal_counts[jur] = count

    if not signal_counts:
        return {"mismatch": False}

    strongest = max(signal_counts, key=signal_counts.get)

    if strongest != selected_jurisdiction.upper() and signal_counts[strongest] >= 2:
        return {
            "mismatch": True,
            "selected": selected_jurisdiction,
            "detected": strongest,
            "confidence": signal_counts[strongest],
            "warning": (
                f"Your description contains terms associated with "
                f"{strongest} construction. You selected "
                f"{selected_jurisdiction}. Please confirm your "
                f"jurisdiction before generating."
            ),
        }

    return {"mismatch": False}
