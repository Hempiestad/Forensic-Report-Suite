#!/usr/bin/env python3
"""
Quick Resolution Validator - CLI Tool
Fast command-line resolution validation without GUI overhead
Useful for CI/CD and automated testing
"""

import sys
import json
import argparse
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResolutionCheck:
    """Results of checking a resolution"""
    name: str
    width: int
    height: int
    supported: bool
    reason: str
    suggestions: List[str]


class ResolutionValidator:
    """Validates resolutions against known constraints"""
    
    # Your application constraints
    MIN_WIDTH = 1400
    MIN_HEIGHT = 900
    RECOMMENDED_MIN = (1400, 900)
    TYPICAL_MAX = (3840, 2160)  # 4K
    
    # Critical aspect ratios to check
    STANDARD_ASPECTS = [
        (4, 3),     # Older
        (5, 4),     # SXGA
        (16, 10),   # Widescreen
        (16, 9),    # HD/Modern
    ]
    
    def __init__(self):
        self.checks: List[ResolutionCheck] = []
    
    def validate_resolution(self, width: int, height: int, name: str = "") -> ResolutionCheck:
        """Validate a single resolution"""
        
        if not name:
            name = f"{width}x{height}"
        
        issues = []
        suggestions = []
        
        # Check minimum
        if width < 800 or height < 600:
            issues.append("Resolution is extremely small (below 800x600)")
            suggestions.append("Not suitable for modern desktop applications")
            return ResolutionCheck(
                name=name,
                width=width,
                height=height,
                supported=False,
                reason="Below minimum viable resolution",
                suggestions=suggestions
            )
        
        # Check against minimum
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            issues.append(
                f"Resolution {width}x{height} below minimum ({self.MIN_WIDTH}x{self.MIN_HEIGHT})"
            )
            suggestions.append(f"Increase resolution to at least {self.MIN_WIDTH}x{self.MIN_HEIGHT}")
            suggestions.append("Content may not fit properly")
        
        # Check aspect ratio
        gcd = self._gcd(width, height)
        aspect_w = width // gcd
        aspect_h = height // gcd
        
        matching_aspect = False
        for std_w, std_h in self.STANDARD_ASPECTS:
            if aspect_w == std_w and aspect_h == std_h:
                matching_aspect = True
                break
        
        if not matching_aspect:
            suggestions.append(
                f"Unusual aspect ratio {aspect_w}:{aspect_h} "
                f"(standard ratios: 4:3, 5:4, 16:10, 16:9)"
            )
        
        # Check for extreme aspect ratios (ultra-wide)
        if width > height * 2:
            suggestions.append("Ultra-wide aspect ratio detected - test horizontal scrolling")
        elif height > width:
            suggestions.append("Vertical aspect ratio - unusual for typical desktop apps")
        
        # Megapixel check (rough DPI estimation)
        megapixels = (width * height) / 1_000_000
        if megapixels < 0.3:
            issues.append(f"Very low resolution ({megapixels:.2f} megapixels)")
            suggestions.append("Not recommended for professional applications")
        elif megapixels > 8:
            suggestions.append(f"High resolution ({megapixels:.2f} megapixels) - test DPI scaling")
        
        supported = len(issues) == 0
        reason = "; ".join(issues) if issues else "OK"
        
        check = ResolutionCheck(
            name=name,
            width=width,
            height=height,
            supported=supported,
            reason=reason,
            suggestions=suggestions
        )
        
        self.checks.append(check)
        return check
    
    def validate_batch(self, resolutions: Dict[str, Tuple[int, int]]) -> List[ResolutionCheck]:
        """Validate multiple resolutions"""
        for name, (width, height) in resolutions.items():
            self.validate_resolution(width, height, name)
        return self.checks
    
    @staticmethod
    def _gcd(a: int, b: int) -> int:
        """Calculate greatest common divisor"""
        while b:
            a, b = b, a % b
        return a
    
    def print_report(self, verbose: bool = False):
        """Print validation report"""
        print("\n" + "=" * 80)
        print("RESOLUTION VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\nApplication Constraints:")
        print(f"  Minimum supported: {self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        print(f"  Typical maximum: {self.TYPICAL_MAX[0]}x{self.TYPICAL_MAX[1]}")
        
        if not self.checks:
            print("\nNo resolutions to validate.")
            return
        
        supported = sum(1 for c in self.checks if c.supported)
        total = len(self.checks)
        
        print(f"\n{'-' * 80}")
        print(f"RESULTS: {supported}/{total} resolutions supported ({supported/total*100:.0f}%)")
        print(f"{'-' * 80}")
        
        for check in sorted(self.checks, key=lambda c: c.width * c.height):
            status = "✓" if check.supported else "✗"
            print(f"\n{status} {check.name}: {check.width}x{check.height}")
            
            if check.reason != "OK":
                print(f"   Issue: {check.reason}")
            
            if check.suggestions and verbose:
                for i, suggestion in enumerate(check.suggestions, 1):
                    print(f"   Tip {i}: {suggestion}")
        
        print("\n" + "=" * 80)
    
    def get_json_report(self) -> str:
        """Get results as JSON"""
        data = {
            'constraints': {
                'minimum': f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}",
                'typical_maximum': f"{self.TYPICAL_MAX[0]}x{self.TYPICAL_MAX[1]}"
            },
            'results': [
                {
                    'name': c.name,
                    'resolution': f"{c.width}x{c.height}",
                    'supported': c.supported,
                    'issue': c.reason,
                    'suggestions': c.suggestions
                }
                for c in sorted(self.checks, key=lambda c: c.width * c.height)
            ],
            'summary': {
                'total': len(self.checks),
                'supported': sum(1 for c in self.checks if c.supported),
                'unsupported': sum(1 for c in self.checks if not c.supported)
            }
        }
        return json.dumps(data, indent=2)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Quick resolution validator for Forensic Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a single resolution
  python resolution_validator.py -w 1920 -h 1080
  
  # Test multiple custom resolutions
  python resolution_validator.py -c 1600x900 1920x1080 2560x1440
  
  # Test all standard resolutions
  python resolution_validator.py --standard
  
  # Get JSON output
  python resolution_validator.py --standard --json > results.json
  
  # Verbose output with suggestions
  python resolution_validator.py --standard -v
        """
    )
    
    parser.add_argument(
        '-w', '--width',
        type=int,
        help='Test width in pixels'
    )
    parser.add_argument(
        '-h', '--height',
        type=int,
        help='Test height in pixels'
    )
    parser.add_argument(
        '-c', '--custom',
        nargs='+',
        help='Custom resolutions to test (e.g., 1920x1080 1366x768)'
    )
    parser.add_argument(
        '-s', '--standard',
        action='store_true',
        help='Test all standard resolutions'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed suggestions'
    )
    
    args = parser.parse_args()
    
    validator = ResolutionValidator()
    
    # Handle input
    if args.standard:
        # Test all standard resolutions
        standard_res = {
            "600x480": (600, 480),
            "1024x768": (1024, 768),
            "1280x720": (1280, 720),
            "1366x768": (1366, 768),
            "1400x900 (Min)": (1400, 900),
            "1600x900": (1600, 900),
            "1920x1080": (1920, 1080),
            "2560x1440": (2560, 1440),
            "3840x2160": (3840, 2160),
        }
        validator.validate_batch(standard_res)
    
    elif args.custom:
        # Test custom resolutions
        for res_str in args.custom:
            try:
                w, h = map(int, res_str.split('x'))
                validator.validate_resolution(w, h, res_str)
            except ValueError:
                print(f"Error parsing resolution '{res_str}'. Use format: WIDTHxHEIGHT")
                sys.exit(1)
    
    elif args.width and args.height:
        # Test single resolution
        validator.validate_resolution(args.width, args.height)
    
    else:
        # Default: test current minimum
        validator.validate_resolution(1400, 900, "1400x900 (Current Minimum)")
    
    # Output results
    if args.json:
        print(validator.get_json_report())
    else:
        validator.print_report(verbose=args.verbose)


if __name__ == "__main__":
    main()
