"""
Address Normalization Service

Normalizes property addresses to a standard format for matching.
Handles variations like "St" vs "Street", case differences, extra spaces, etc.

Example:
    "123 Main St, Anytown, FL 12345" → "123 MAIN STREET, ANYTOWN, FL 12345"
"""

import re
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ParsedAddress:
    """Parsed address components"""
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    street_suffix: Optional[str] = None
    unit_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    normalized_address: str = ""


class AddressNormalizer:
    """
    Service for normalizing addresses to a standard format.

    Normalization rules:
    - Convert to uppercase
    - Expand common street suffix abbreviations
    - Remove extra whitespace
    - Standardize directional prefixes (N, S, E, W, NE, etc.)
    """

    # Street suffix abbreviations to expand
    STREET_SUFFIXES = {
        'ST': 'STREET',
        'AVE': 'AVENUE',
        'BLVD': 'BOULEVARD',
        'RD': 'ROAD',
        'DR': 'DRIVE',
        'LN': 'LANE',
        'CT': 'COURT',
        'CIR': 'CIRCLE',
        'PL': 'PLACE',
        'TER': 'TERRACE',
        'WAY': 'WAY',
        'PKWY': 'PARKWAY',
        'HWY': 'HIGHWAY',
        'SQ': 'SQUARE',
        'TR': 'TRAIL',
        'TPKE': 'TURNPIKE',
        'LOOP': 'LOOP',
        'PATH': 'PATH',
        'ALY': 'ALLEY',
        'XING': 'CROSSING',
        'PASS': 'PASS',
        'RUN': 'RUN',
        'ROW': 'ROW',
    }

    # Directional prefixes/suffixes
    DIRECTIONALS = {
        'N': 'NORTH',
        'S': 'SOUTH',
        'E': 'EAST',
        'W': 'WEST',
        'NE': 'NORTHEAST',
        'NW': 'NORTHWEST',
        'SE': 'SOUTHEAST',
        'SW': 'SOUTHWEST',
    }

    # Unit/apartment indicators
    UNIT_INDICATORS = [
        'APT', 'APARTMENT', 'UNIT', 'STE', 'SUITE', '#', 'BLDG', 'BUILDING', 'FL', 'FLOOR'
    ]

    @classmethod
    def normalize(cls, address: str) -> str:
        """
        Normalize an address to a standard format for matching.

        Args:
            address: Raw address string

        Returns:
            Normalized address string (uppercase, expanded abbreviations)
        """
        if not address:
            return ""

        # Convert to uppercase
        normalized = address.upper().strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Expand street suffix abbreviations
        for abbrev, full in cls.STREET_SUFFIXES.items():
            # Match abbreviation as whole word (with word boundaries)
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            normalized = re.sub(pattern, full, normalized)

        # Expand directional abbreviations
        for abbrev, full in cls.DIRECTIONALS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            normalized = re.sub(pattern, full, normalized)

        # Remove punctuation (except # for unit numbers)
        normalized = re.sub(r'[,.]', '', normalized)

        # Clean up extra spaces again
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    @classmethod
    def parse_address(cls, address: str) -> ParsedAddress:
        """
        Parse an address into components and return normalized version.

        Args:
            address: Raw address string

        Returns:
            ParsedAddress object with components and normalized address
        """
        if not address:
            return ParsedAddress()

        # First normalize the address
        normalized = cls.normalize(address)

        parsed = ParsedAddress(normalized_address=normalized)

        # Split into parts
        parts = normalized.split()

        if not parts:
            return parsed

        # Extract street number (first numeric part)
        street_number_match = re.match(r'^(\d+[A-Z]?)', parts[0])
        if street_number_match:
            parsed.street_number = street_number_match.group(1)
            parts = parts[1:]  # Remove street number from parts

        # Look for unit indicators
        unit_idx = None
        for i, part in enumerate(parts):
            if part in cls.UNIT_INDICATORS or part.startswith('#'):
                unit_idx = i
                break

        # Extract unit number if found
        if unit_idx is not None:
            # Unit number is everything from unit indicator onwards
            unit_parts = parts[unit_idx:]
            if len(unit_parts) > 1:
                parsed.unit_number = ' '.join(unit_parts[1:])
            parts = parts[:unit_idx]  # Remove unit from parts

        # Look for state (2-letter code)
        state_idx = None
        for i, part in enumerate(parts):
            if len(part) == 2 and part.isalpha():
                # Likely a state code
                state_idx = i
                parsed.state = part
                break

        # Look for ZIP code (5 digits or 5+4 format)
        zip_idx = None
        for i, part in enumerate(parts):
            if re.match(r'^\d{5}(-\d{4})?$', part):
                zip_idx = i
                parsed.zip_code = part
                break

        # Extract city (everything between street and state/zip)
        if state_idx is not None or zip_idx is not None:
            # City is between street suffix and state/zip
            city_start_idx = None

            # Find where street ends (look for known suffixes)
            for i, part in enumerate(parts):
                if part in cls.STREET_SUFFIXES.values():
                    city_start_idx = i + 1
                    break

            if city_start_idx is not None:
                city_end_idx = state_idx if state_idx is not None else zip_idx
                if city_start_idx < city_end_idx:
                    parsed.city = ' '.join(parts[city_start_idx:city_end_idx])

        # Extract street name and suffix
        # Street is from after street number to before city/unit
        street_parts = []
        for i, part in enumerate(parts):
            # Stop at city, state, zip, or unit
            if (state_idx is not None and i >= state_idx) or \
               (zip_idx is not None and i >= zip_idx) or \
               (parsed.city and part in parsed.city.split()):
                break
            street_parts.append(part)

        if street_parts:
            # Last part might be suffix
            if street_parts[-1] in cls.STREET_SUFFIXES.values():
                parsed.street_suffix = street_parts[-1]
                parsed.street_name = ' '.join(street_parts[:-1])
            else:
                parsed.street_name = ' '.join(street_parts)

        return parsed

    @classmethod
    def are_addresses_same(cls, address1: str, address2: str) -> bool:
        """
        Check if two addresses are the same after normalization.

        Args:
            address1: First address
            address2: Second address

        Returns:
            True if addresses match after normalization
        """
        norm1 = cls.normalize(address1)
        norm2 = cls.normalize(address2)
        return norm1 == norm2

    @classmethod
    def extract_components(cls, address: str) -> Dict[str, Optional[str]]:
        """
        Extract address components as a dictionary.

        Args:
            address: Raw address string

        Returns:
            Dictionary with address components
        """
        parsed = cls.parse_address(address)
        return {
            'street_number': parsed.street_number,
            'street_name': parsed.street_name,
            'street_suffix': parsed.street_suffix,
            'unit_number': parsed.unit_number,
            'city': parsed.city,
            'state': parsed.state,
            'zip_code': parsed.zip_code,
            'normalized_address': parsed.normalized_address,
        }
