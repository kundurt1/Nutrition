# nutrition-backend/services/unit_converter.py

from typing import Optional, List


class UnitConverterService:
    """Service for handling unit conversions"""

    # Volume conversions (everything to milliliters)
    VOLUME_CONVERSIONS = {
        'ml': 1.0, 'milliliter': 1.0, 'milliliters': 1.0,
        'l': 1000.0, 'liter': 1000.0, 'liters': 1000.0,
        'cup': 236.588, 'cups': 236.588,
        'tbsp': 14.787, 'tablespoon': 14.787, 'tablespoons': 14.787,
        'tsp': 4.929, 'teaspoon': 4.929, 'teaspoons': 4.929,
        'fl oz': 29.574, 'fluid ounce': 29.574, 'fluid ounces': 29.574,
        'pint': 473.176, 'pints': 473.176,
        'quart': 946.353, 'quarts': 946.353,
        'gallon': 3785.41, 'gallons': 3785.41
    }

    # Weight conversions (everything to grams)
    WEIGHT_CONVERSIONS = {
        'g': 1.0, 'gram': 1.0, 'grams': 1.0,
        'kg': 1000.0, 'kilogram': 1000.0, 'kilograms': 1000.0,
        'oz': 28.35, 'ounce': 28.35, 'ounces': 28.35,
        'lb': 453.592, 'pound': 453.592, 'pounds': 453.592,
        'lbs': 453.592
    }

    # Length conversions (everything to millimeters)
    LENGTH_CONVERSIONS = {
        'mm': 1.0, 'millimeter': 1.0, 'millimeters': 1.0,
        'cm': 10.0, 'centimeter': 10.0, 'centimeters': 10.0,
        'inch': 25.4, 'inches': 25.4, 'in': 25.4,
        'ft': 304.8, 'foot': 304.8, 'feet': 304.8
    }

    # Count-based units (pieces, items, etc.)
    COUNT_UNITS = {
        'piece', 'pieces', 'item', 'items', 'whole', 'large', 'medium', 'small',
        'clove', 'cloves', 'head', 'heads', 'bunch', 'bunches', 'sheet', 'sheets'
    }

    def get_unit_type(self, unit: str) -> str:
        """Determine the type of unit (volume, weight, length, count)"""
        unit_lower = unit.lower().strip()

        if unit_lower in self.VOLUME_CONVERSIONS:
            return 'volume'
        elif unit_lower in self.WEIGHT_CONVERSIONS:
            return 'weight'
        elif unit_lower in self.LENGTH_CONVERSIONS:
            return 'length'
        elif unit_lower in self.COUNT_UNITS:
            return 'count'
        else:
            return 'unknown'

    def convert_units(self, quantity: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convert quantity from one unit to another"""
        from_unit_lower = from_unit.lower().strip()
        to_unit_lower = to_unit.lower().strip()

        # If units are the same, return original quantity
        if from_unit_lower == to_unit_lower:
            return quantity

        # Determine unit types
        from_type = self.get_unit_type(from_unit)
        to_type = self.get_unit_type(to_unit)

        # Can only convert within same unit type
        if from_type != to_type or from_type == 'unknown':
            return None

        # Handle count units (no conversion needed)
        if from_type == 'count':
            return quantity

        # Get conversion factors
        if from_type == 'volume':
            from_factor = self.VOLUME_CONVERSIONS.get(from_unit_lower)
            to_factor = self.VOLUME_CONVERSIONS.get(to_unit_lower)
        elif from_type == 'weight':
            from_factor = self.WEIGHT_CONVERSIONS.get(from_unit_lower)
            to_factor = self.WEIGHT_CONVERSIONS.get(to_unit_lower)
        elif from_type == 'length':
            from_factor = self.LENGTH_CONVERSIONS.get(from_unit_lower)
            to_factor = self.LENGTH_CONVERSIONS.get(to_unit_lower)
        else:
            return None

        if from_factor is None or to_factor is None:
            return None

        # Convert: quantity * from_factor / to_factor
        return quantity * from_factor / to_factor

    def get_compatible_units(self, unit: str) -> List[str]:
        """Get list of units that can be converted to/from the given unit"""
        unit_type = self.get_unit_type(unit)

        if unit_type == 'volume':
            return list(self.VOLUME_CONVERSIONS.keys())
        elif unit_type == 'weight':
            return list(self.WEIGHT_CONVERSIONS.keys())
        elif unit_type == 'length':
            return list(self.LENGTH_CONVERSIONS.keys())
        elif unit_type == 'count':
            return list(self.COUNT_UNITS)
        else:
            return []